"""
ROLE005 — Agent 共用的 LLM 调用封装。

支持 OpenAI 兼容 ``response_format``（如 ``json_object``），降低 Planner/Evaluator 等 JSON 产物解析失败率。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage

from app.session.role.role005.config import resolve_role005_llm_response_format
from app.session.role.role_util.bindings import GraphBindings, is_cancelled

log = logging.getLogger(__name__)


def _is_unsupported_response_format_error(exc: BaseException) -> bool:
    """当前模型/网关不支持 response_format 时，可回退为普通文本调用。"""
    msg = str(exc).lower()
    needles = (
        "response_format",
        "json_schema",
        "json_object",
        "structured outputs",
        "not supported",
        "unsupported",
        "invalid parameter",
    )
    return any(n in msg for n in needles)


def invoke_llm_text(
    bindings: GraphBindings,
    prompt: str,
    *,
    response_format: Optional[Dict[str, Any]] = None,
) -> str:
    """
    同步调用绑定 LLM，返回文本；取消时返回空串。

    参数
    ----
    response_format:
        传给底层 Chat 模型的 OpenAI 兼容参数，例如 ``{"type": "json_object"}``。
        为 None 时不约束输出格式。
    """
    if is_cancelled(bindings):
        return ""
    messages = [HumanMessage(content=prompt)]
    if not response_format:
        msg = bindings.llm.invoke(messages)
        return str(getattr(msg, "content", msg) or "").strip()

    try:
        msg = bindings.llm.invoke(messages, response_format=response_format)
        return str(getattr(msg, "content", msg) or "").strip()
    except Exception as exc:
        if not _is_unsupported_response_format_error(exc):
            raise
        log.warning(
            "ROLE005 response_format=%s 不可用，回退普通调用: %s",
            response_format.get("type"),
            exc,
        )
        msg = bindings.llm.invoke(messages)
        return str(getattr(msg, "content", msg) or "").strip()


def invoke_llm_json_object(bindings: GraphBindings, prompt: str) -> str:
    """
    以 JSON 对象模式调用 LLM（``response_format={"type": "json_object"}``）。

    用于 Planner / Interviewer / Evaluator 等必须输出 JSON 的 Agent。
    是否启用由 ``ROLE005_LLM_RESPONSE_FORMAT`` 控制（默认 json_object）；
    设为 none/off 时与 ``invoke_llm_text`` 相同，仅依赖 Prompt 约束。
    """
    fmt = resolve_role005_llm_response_format()
    return invoke_llm_text(bindings, prompt, response_format=fmt)
