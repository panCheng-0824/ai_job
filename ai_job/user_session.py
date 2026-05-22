"""
用户会话编排层：读取 ``usermodel.json``，拼装 system + 历史上下文，创建 Agent 并发起本轮提问。

与其它模块的边界：
- **不**直接读 ``modelCfg.json``：模型列表与 ``ChatOpenAI`` 构造由 ``lc_agent.create_agent_executor`` 封装；
- **不**实现单次管道 Chat：去噪/压缩/对抗/画像的 LLM 细节在 ``role_pipeline`` + ``pipeline_llm``；
- 本文件只做「选用户 → 调管道 → 调主 Agent → 汇总额外字段」的顺序控制。

可选 **管道**（由 ``role_profiles.json`` 定义，经 ``user_model.load_role_profiles`` 加载）：

1. **问题去噪**：对「当前问题」做噪声剔除，再作为 ``input`` 交给主 Agent；
2. **上下文压缩**：对 ``context_memory`` 做摘要去噪，再作为 ``chat_history``（概括多轮前情）；
3. **对抗审查**：主 Agent 作答后，红队审查；
4. **画像补充**：综合既有画像、历史摘要、本轮问答（及对抗摘要）给出用户画像优化建议（**仅建议文本**，不写回 JSON）。

数据流简述：
``usermodel.json`` → ``UserModel`` → （可选管道）→ ``create_agent_executor`` → ``invoke``
→ ``adversarial_review`` → ``suggest_profile_enrichment``。
"""

from pathlib import Path
import sys
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from lc_agent import create_agent_executor
from lc_agent.agent_executor_compat import AgentExecutor
from lc_agent.builtin_tools import build_builtin_tools_by_names
from role_pipeline import (
    adversarial_review,
    compress_context_to_messages,
    denoise_question,
    suggest_profile_enrichment,
)
from pipeline_llm import reset_pipeline_trace_id, set_pipeline_trace_id
from app.common.runtime_config import resolve_bool_setting
from app.session.stage_logger import stage_log
from user_model import MemoryTurn, UserModel, build_system_prompt_from_user, load_role_profiles, load_user_model

def _pipeline_stage_logs_enabled(verbose: bool) -> bool:
    """
    控制是否输出管道阶段日志。

    优先级：
    1) 环境变量 ``PIPELINE_STAGE_LOGS``；
    2) ``runtime_config.json`` 的 ``pipeline_stage_logs``；
    3) ``verbose`` 或交互终端状态。
    """
    # 默认行为保持不变：verbose 或交互终端开启日志；
    # 仅当 env/runtime_config 明确设置时覆盖默认。
    return resolve_bool_setting(
        env_key="PIPELINE_STAGE_LOGS",
        config_key="pipeline_stage_logs",
        default=(verbose or sys.stderr.isatty()),
    )


def context_memory_to_messages(memory: List[MemoryTurn]) -> List[BaseMessage]:
    """把 ``context_memory`` 转成 LangChain 消息序列，填入模板的 ``chat_history`` 占位符。"""
    out: List[BaseMessage] = []
    for turn in memory:
        if turn["role"] == "user":
            out.append(HumanMessage(content=turn["content"]))
        else:
            out.append(AIMessage(content=turn["content"]))
    return out


def build_invoke_kwargs(
    user: UserModel,
    *,
    question_override: Optional[str] = None,
    chat_history_override: Optional[List[BaseMessage]] = None,
) -> Dict[str, Any]:
    """
    ``AgentExecutor.invoke`` 参数：本轮问题 + 历史上下文。

    ``question_override`` / ``chat_history_override`` 非空时覆盖用户模型中的原文，
    供管道（去噪 / 压缩）之后注入。
    """
    q = question_override if question_override is not None else user.get("current_question", "")
    hist = (
        chat_history_override
        if chat_history_override is not None
        else context_memory_to_messages(user.get("context_memory", []))
    )
    return {"input": q, "chat_history": hist}


def create_agent_from_user_model(
    user_path: Optional[Path] = None,
    *,
    username: Optional[str] = None,
    usercode: Optional[str] = None,
    verbose: bool = False,
    temperature: float = 0.0,
    system_prompt_extra: Optional[str] = None,
) -> Tuple[AgentExecutor, UserModel]:
    """
    基于用户模型文件创建 ``AgentExecutor``。

    - ``username`` / ``usercode``：从 ``usermodel.json`` **数组**中定位用户；都不传则用第一条；
    - ``model_level``：来自 ``UserModel.model_level``，对应 ``modelCfg.json`` 档位；
    - ``system_prompt``：标识 + 画像 + 目标 + sys_prompt + user_prompt 的合成文本；
    - ``with_chat_history``：固定为 True，invoke 时传入 ``context_memory`` 转换后的消息（可为空列表）。
    """
    user = load_user_model(user_path, username=username, usercode=usercode)
    system_prompt = build_system_prompt_from_user(user)
    extra = (system_prompt_extra or "").strip()
    if extra:
        system_prompt = system_prompt + "\n\n" + extra
    user_tool_names = [str(name).strip() for name in user.get("tools", []) if str(name).strip()]
    user_tools = build_builtin_tools_by_names(user_tool_names) if user_tool_names else None
    executor = create_agent_executor(
        model_level=user["model_level"],
        tools=user_tools,
        system_prompt=system_prompt,
        with_chat_history=True,
        verbose=verbose,
        temperature=temperature,
    )
    return executor, user


def run_user_query(
    user_path: Optional[Path] = None,
    *,
    username: Optional[str] = None,
    usercode: Optional[str] = None,
    verbose: bool = False,
    temperature: float = 0.0,
    use_role_pipeline: bool = True,
    role_profiles_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    读取用户模型、创建 Agent，执行一轮 ``invoke``。

    :param use_role_pipeline: 为 True 时启用 ``role_profiles.json`` 中的管道角色
        （去噪 → 压缩上下文 → 主 Agent → 对抗审查 → 画像补充建议）。
    """
    executor, user = create_agent_from_user_model(
        user_path,
        username=username,
        usercode=usercode,
        verbose=verbose,
        temperature=temperature,
    )

    if not use_role_pipeline:
        # 最短路径：不跑四段管道，直接以「原文问题 + 原始 memory 转消息」调用主 Agent
        return executor.invoke(build_invoke_kwargs(user))

    # 以下：顺序固定——先文本预处理再主对话，主对话后再审计与画像建议
    stage_logs = _pipeline_stage_logs_enabled(verbose)
    trace_id = uuid.uuid4().hex[:12]
    trace_token = set_pipeline_trace_id(trace_id)
    try:
        profiles = load_role_profiles(role_profiles_path)
        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "question_denoiser", "start")
        denoised = denoise_question(user.get("current_question", ""), profiles["question_denoiser"])
        stage_log(stage_logs, trace_id, "question_denoiser", "finish", _stage_started)

        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "context_compressor", "start")
        hist_msgs, summary_text = compress_context_to_messages(
            user.get("context_memory", []),
            profiles["context_compressor"],
        )
        stage_log(stage_logs, trace_id, "context_compressor", "finish", _stage_started)

        payload = build_invoke_kwargs(
            user,
            question_override=denoised,
            chat_history_override=hist_msgs,
        )
        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "main_agent", "start")
        result = executor.invoke(payload)
        stage_log(stage_logs, trace_id, "main_agent", "finish", _stage_started)
        agent_out = result.get("output", "")

        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "adversary", "start")
        critique = adversarial_review(str(agent_out), denoised, profiles["adversary"])
        stage_log(stage_logs, trace_id, "adversary", "finish", _stage_started)

        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "profile_enricher", "start")
        profile_hint = suggest_profile_enrichment(
            user,
            denoised_question=denoised,
            agent_answer=str(agent_out),
            context_summary=summary_text,
            profile=profiles["profile_enricher"],
            adversarial_review_text=critique,
        )
        stage_log(stage_logs, trace_id, "profile_enricher", "finish", _stage_started)
    finally:
        reset_pipeline_trace_id(trace_token)

    merged: Dict[str, Any] = dict(result)
    merged["pipeline"] = {
        "trace_id": trace_id,
        "roles_loaded_from": str(role_profiles_path or "default role_profiles.json"),
        "original_question": user.get("current_question", ""),
        "denoised_question": denoised,
        "context_compression_summary": summary_text,
        "used_compressed_history": bool(user.get("context_memory", [])),
    }
    merged["adversarial_review"] = critique
    merged["profile_enrichment"] = profile_hint
    return merged


def run_user_query_for_runtime_session(
    *,
    usercode: str,
    question: str,
    context_memory: List[MemoryTurn],
    verbose: bool = False,
    temperature: float = 0.0,
    use_role_pipeline: bool = True,
    role_profiles_path: Optional[Path] = None,
    system_prompt_extra: Optional[str] = None,
) -> Dict[str, Any]:
    """
    会话态调用入口：以 ``usercode`` 选中角色后，用运行时的 ``question/context_memory`` 执行核心链路。

    该函数用于 Web chat service，保持与 ``run_user_query`` 的核心流程一致，但不依赖
    ``usermodel.json`` 中持久化的 ``current_question/context_memory``。
    """
    executor, user = create_agent_from_user_model(
        usercode=usercode,
        verbose=verbose,
        temperature=temperature,
        system_prompt_extra=system_prompt_extra,
    )
    runtime_question = (question or "").strip()
    runtime_memory = context_memory or []

    if not use_role_pipeline:
        payload = build_invoke_kwargs(
            user,
            question_override=runtime_question,
            chat_history_override=context_memory_to_messages(runtime_memory),
        )
        return executor.invoke(payload)

    stage_logs = _pipeline_stage_logs_enabled(verbose)
    trace_id = uuid.uuid4().hex[:12]
    trace_token = set_pipeline_trace_id(trace_id)
    try:
        profiles = load_role_profiles(role_profiles_path)
        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "question_denoiser", "start")
        denoised = denoise_question(runtime_question, profiles["question_denoiser"])
        stage_log(stage_logs, trace_id, "question_denoiser", "finish", _stage_started)

        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "context_compressor", "start")
        hist_msgs, summary_text = compress_context_to_messages(
            runtime_memory,
            profiles["context_compressor"],
        )
        stage_log(stage_logs, trace_id, "context_compressor", "finish", _stage_started)

        payload = build_invoke_kwargs(
            user,
            question_override=denoised,
            chat_history_override=hist_msgs,
        )
        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "main_agent", "start")
        result = executor.invoke(payload)
        stage_log(stage_logs, trace_id, "main_agent", "finish", _stage_started)
        agent_out = result.get("output", "")

        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "adversary", "start")
        critique = adversarial_review(str(agent_out), denoised, profiles["adversary"])
        stage_log(stage_logs, trace_id, "adversary", "finish", _stage_started)

        _stage_started = time.monotonic()
        stage_log(stage_logs, trace_id, "profile_enricher", "start")
        profile_hint = suggest_profile_enrichment(
            user,
            denoised_question=denoised,
            agent_answer=str(agent_out),
            context_summary=summary_text,
            profile=profiles["profile_enricher"],
            adversarial_review_text=critique,
        )
        stage_log(stage_logs, trace_id, "profile_enricher", "finish", _stage_started)
    finally:
        reset_pipeline_trace_id(trace_token)

    merged: Dict[str, Any] = dict(result)
    merged["pipeline"] = {
        "trace_id": trace_id,
        "roles_loaded_from": str(role_profiles_path or "default role_profiles.json"),
        "original_question": runtime_question,
        "denoised_question": denoised,
        "context_compression_summary": summary_text,
        "used_compressed_history": bool(runtime_memory),
    }
    merged["adversarial_review"] = critique
    merged["profile_enrichment"] = profile_hint
    return merged
