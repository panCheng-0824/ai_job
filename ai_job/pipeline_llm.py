"""
管道专用 LLM 执行层（与「管道业务语义」解耦）。

职责划分：
- **本模块**：根据 ``PipelineRoleProfile`` 选模型、组装 System/Human 消息、可选 JSON Schema 结构化输出；
- **``role_pipeline``**：在之上实现「去噪 / 压缩 / 对抗 / 画像补充」等业务步骤与入参拼装；
- **``user_session``**：编排用户 Agent 与管道调用顺序。

这样单元测试或离线演示可单独 ``patch`` 本模块的 ``run_pipeline_llm``，或通过注入替换（见各调用方）
而不必关心具体去噪文案或压缩格式。
"""

from __future__ import annotations

import json
import sys
import threading
import time
import warnings
from contextvars import ContextVar
from typing import Any, Dict, Union

from langchain_core.messages import HumanMessage, SystemMessage

from lc_agent import chat_model_from_entry, select_model_by_level
from lc_agent.structured_output import bind_json_schema, load_json_schema
from model_cfg import load_model_list
from app.common.runtime_config import (
    resolve_bool_setting,
    resolve_float_setting,
    resolve_int_setting,
)
from user_model import PipelineRoleProfile

_PIPELINE_TRACE_ID: ContextVar[str | None] = ContextVar("pipeline_trace_id", default=None)


def set_pipeline_trace_id(trace_id: str | None) -> object:
    """设置当前上下文 trace_id，返回 token 以便后续 reset。"""
    return _PIPELINE_TRACE_ID.set(trace_id)


def reset_pipeline_trace_id(token: object) -> None:
    """恢复 ``set_pipeline_trace_id`` 之前的 trace_id。"""
    _PIPELINE_TRACE_ID.reset(token)


def get_pipeline_trace_id() -> str | None:
    """获取当前上下文中的 trace_id。"""
    return _PIPELINE_TRACE_ID.get()


def _is_progress_enabled() -> bool:
    """
    控制是否打印 LLM 调用进度。

    - 环境变量 ``PIPELINE_LLM_PROGRESS`` 优先（1/true/on 开启；0/false/off 关闭）；
    - 未设置时，仅在交互终端（TTY）启用，避免测试日志噪音。
    """
    return resolve_bool_setting(
        env_key="PIPELINE_LLM_PROGRESS",
        config_key="pipeline_llm_progress",
        default=sys.stderr.isatty(),
    )


def _warn_after_seconds() -> float:
    """慢调用告警阈值（秒）；默认 30 秒，可由环境变量覆盖。"""
    return resolve_float_setting(
        env_key="PIPELINE_LLM_WARN_AFTER_S",
        config_key="pipeline_llm_warn_after_s",
        default=30.0,
        min_value=0.0,
    )


def _request_timeout_seconds() -> float:
    """
    LLM 单次请求超时（秒）。

    优先级：``PIPELINE_LLM_TIMEOUT_S`` > ``runtime_config.json.pipeline_llm_timeout_s`` > 默认 25s。
    """
    return resolve_float_setting(
        env_key="PIPELINE_LLM_TIMEOUT_S",
        config_key="pipeline_llm_timeout_s",
        default=25.0,
        min_value=0.0,
    )


def _max_retries() -> int:
    """
    LLM 请求重试次数，默认 0（避免长时间等待时被隐式重试放大）。
    """
    return resolve_int_setting(
        env_key="PIPELINE_LLM_MAX_RETRIES",
        config_key="pipeline_llm_max_retries",
        default=0,
        min_value=0,
    )


def _skip_structured_output() -> bool:
    """
    是否跳过 ``with_structured_output(json_schema)``，整条管道只做普通 Chat。

    本地 OpenAI 兼容端对 ``json_schema`` 往往更慢或不稳定；设为 True 可显著缩短等待。
    优先级：``PIPELINE_LLM_SKIP_STRUCTURED`` > ``runtime_config.pipeline_llm_skip_structured`` > False。
    """
    return resolve_bool_setting(
        env_key="PIPELINE_LLM_SKIP_STRUCTURED",
        config_key="pipeline_llm_skip_structured",
        default=False,
    )


def _estimate_payload_chars(messages: list[Any]) -> int:
    """粗略估算消息体字符数，作为慢调用诊断信息。"""
    total = 0
    for m in messages:
        content = getattr(m, "content", "")
        if isinstance(content, str):
            total += len(content)
        else:
            total += len(str(content))
    return total


def _invoke_with_progress(runnable: Any, messages: list[Any], *, label: str) -> Any:
    """为阻塞式 ``invoke`` 增加可见进度心跳，便于长耗时排障。"""
    if not _is_progress_enabled():
        return runnable.invoke(messages)

    stop = threading.Event()
    started = time.monotonic()
    payload_chars = _estimate_payload_chars(messages)
    warn_after_s = _warn_after_seconds()
    warned = False
    trace_id = get_pipeline_trace_id() or "-"

    def _heartbeat() -> None:
        nonlocal warned
        while not stop.wait(3.0):
            waited = int(time.monotonic() - started)
            print(
                f"[pipeline_llm][trace={trace_id}] {label} still running... {waited}s",
                file=sys.stderr,
                flush=True,
            )
            if not warned and waited >= warn_after_s:
                warned = True
                print(
                    f"[pipeline_llm][warn][trace={trace_id}] {label} exceeded {warn_after_s:.0f}s "
                    f"(payload_chars={payload_chars})",
                    file=sys.stderr,
                    flush=True,
                )

    worker = threading.Thread(target=_heartbeat, name="pipeline-llm-heartbeat", daemon=True)
    print(
        f"[pipeline_llm][trace={trace_id}] {label} started (payload_chars={payload_chars})",
        file=sys.stderr,
        flush=True,
    )
    worker.start()
    try:
        return runnable.invoke(messages)
    finally:
        stop.set()
        elapsed = time.monotonic() - started
        print(
            f"[pipeline_llm][trace={trace_id}] {label} finished in {elapsed:.2f}s",
            file=sys.stderr,
            flush=True,
        )


def format_structured_to_string(profile: PipelineRoleProfile, data: Any) -> str:
    """
    将单次 LLM 调用的返回值统一成**下游可用的字符串**。

    规则：
    - 若已是 ``str``：strip 后返回；
    - 若为 ``dict`` 且配置了 ``structured_primary_field``：优先取该键（标量会转 JSON 字符串）；
    - 其它对象或整段 dict：格式化为可读 JSON（与 schema 对齐时便于日志与链式传递）。

    与 ``role_profiles.json`` 中 ``structured_primary_field`` 字段一一对应。
    """
    if isinstance(data, str):
        return data.strip()
    if not isinstance(data, dict):
        return str(data).strip()

    primary = profile.get("structured_primary_field")
    if primary and primary in data:
        val = data[primary]
        if isinstance(val, str):
            return val.strip()
        if val is not None:
            return json.dumps(val, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False, indent=2)

#根据 profile 获取配置模型进行回答
def run_pipeline_llm(
    profile: PipelineRoleProfile,
    user_payload: str,
    *,
    temperature: float = 0.0,
) -> Union[str, Dict[str, Any]]:
    """
    执行**单轮**管道角色 Chat：system = 角色 ``sys_prompt``，human = 业务侧拼好的正文。

    返回类型：
    - 若配置了 ``output_schema_path``：尽量返回 **dict**（结构化 JSON 对象）；
    - 否则返回 **str**（普通文本 completion）。

    容错：结构化绑定或调用失败时告警并回退为普通文本生成，避免整条用户请求失败。

    若本地兼容端 ``json_schema`` 模式明显变慢或超时，可设置环境变量
    ``PIPELINE_LLM_SKIP_STRUCTURED=1`` 或 ``runtime_config.json`` 中
    ``pipeline_llm_skip_structured: true``，跳过结构化仅走普通 Chat（等待时间通常明显缩短）。
    """
    entries = load_model_list()
    entry = select_model_by_level(entries, profile["model_level"])
    base = chat_model_from_entry(
        entry,
        temperature=temperature,
        timeout=_request_timeout_seconds(),
        max_retries=_max_retries(),
    )

    schema_rel = profile.get("output_schema_path")
    system_content = profile["sys_prompt"]
    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_payload),
    ]

    if schema_rel and not _skip_structured_output():
        # 明确要求只产出 schema 内字段，减少兼容端「多嘴」解释
        system_content = (
            system_content
            + "\n\n你必须输出符合给定 JSON Schema 的字段；不要输出 Schema 之外的无关说明。"
        )
        messages[0] = SystemMessage(content=system_content)
        try:
            schema = load_json_schema(schema_rel)
            structured = bind_json_schema(base, schema)
            out = _invoke_with_progress(
                structured,
                messages,
                label=f"{profile.get('usercode', 'unknown')} structured invoke",
            )
            if isinstance(out, dict):
                return out
            if isinstance(out, str):
                return out.strip()
            return {}
        except Exception as exc:
            warnings.warn(
                f"structured output failed for {profile.get('usercode')}, fallback to plain text: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
    elif schema_rel and _skip_structured_output():
        trace_id = get_pipeline_trace_id() or "-"
        print(
            f"[pipeline_llm][trace={trace_id}] skip structured output "
            f"(PIPELINE_LLM_SKIP_STRUCTURED / runtime_config.pipeline_llm_skip_structured)",
            file=sys.stderr,
            flush=True,
        )

    try:
        msg = _invoke_with_progress(
            base,
            messages,
            label=f"{profile.get('usercode', 'unknown')} plain invoke",
        )
        text = getattr(msg, "content", None)
        return (text or "").strip()
    except Exception as exc:
        warnings.warn(
            f"plain output failed for {profile.get('usercode')}, return empty text: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return ""
