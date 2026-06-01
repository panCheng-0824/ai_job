"""
ROLE005 — SSE 流式入口（组装 LLM、绑定、按模式分发迭代器）。
"""

from __future__ import annotations

from threading import Event
from typing import Any, Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role005.bindings import build_graph_bindings
from app.session.role.role005.config import interview_enabled, resolve_role005_llm_timeout_seconds
from app.session.role.role005.materials import (
    build_interview_materials_block,
    parse_interview_turn_from_context,
)
from app.session.role.role005.stream_handlers.chat_tokens import iter_chat_tokens
from app.session.role.role005.stream_handlers.mode import detect_stream_mode
from app.session.role.role005.stream_handlers.plan_preview import iter_plan_preview_tokens
from app.session.role.role005.materials.interview_mode import (
    merge_turn_ctx_from_mode,
    parse_interview_mode_context,
)
from app.session.role.role005.stream_handlers.interview_mode_loop import (
    iter_interview_mode_tokens,
)
from app.session.role.role005.stream_handlers.turn_loop import iter_turn_tokens
from app.session.role.role_util.stream_common import (
    ChatTokenStreamContext,
    merge_stream_user,
    prepare_question_and_history,
    role_display_name,
)
from lc_agent import chat_model_from_entry
from lc_agent.selection import select_model_by_level
from model_cfg import load_model_list
from pipeline_llm import _max_retries
from user_model import build_system_prompt_from_user


def stream_chat_service_tokens(ctx: ChatStreamRunContext) -> ChatTokenStreamContext:
    """
    ROLE005 专用流式入口（由 chat_stream_pipeline 按 usercode 调用）。

    业务写入不在此完成；正式流程应走 server_job ``POST /api/interview/{id}/turn``。
    """
    merged_user = merge_stream_user(ctx)
    if not interview_enabled():
        return _disabled_stream_context(ctx, merged_user)

    model_level = str(merged_user.get("model_level", "mid"))
    entry = select_model_by_level(load_model_list(), model_level)
    question, history_block = prepare_question_and_history(ctx, merged_user=merged_user)

    # 学生档案摘要拼入系统提示（与 ROLE001/004 一致）
    profile_extra = (ctx.system_prompt_extra or "").strip()
    role_sys = build_system_prompt_from_user(merged_user)
    if profile_extra:
        role_sys = f"{role_sys}\n\n{profile_extra}"
    _ = role_sys  # 当前图节点用 bindings.role_block；保留以备后续入口节点使用

    materials_block = build_interview_materials_block(
        message_context=ctx.user_message_context,
        context_cards=ctx.user_context_cards,
    )
    mode_ctx = parse_interview_mode_context(ctx.user_message_context or "")
    if mode_ctx:
        turn_ctx = merge_turn_ctx_from_mode(mode_ctx)
    else:
        turn_ctx = parse_interview_turn_from_context(ctx.user_message_context or "")
    mode = detect_stream_mode(ctx.user_display_content, ctx.user_context_cards, turn_ctx)

    llm = chat_model_from_entry(
        entry,
        temperature=max(0.0, min(float(ctx.temperature), 1.0)),
        timeout=resolve_role005_llm_timeout_seconds(merged_user),
        max_retries=_max_retries(),
    )
    cancel_event = Event()
    bindings = build_graph_bindings(
        merged_user, llm, cancel_event, history_block=history_block
    )
    role_label = role_display_name(merged_user, fallback="模拟面试官")
    student_id = str(merged_user.get("student_id") or ctx.student_id or "").strip()
    session_id = str(merged_user.get("session_id") or ctx.session_id or "").strip()

    def cancel() -> None:
        cancel_event.set()

    def iter_tokens() -> Iterator[Dict[str, str]]:
        yield {
            "type": "thinking",
            "content": f"【{role_label}】正在处理（模式={mode}）…\n",
        }
        try:
            if mode == "plan_preview":
                yield from iter_plan_preview_tokens(
                    ctx,
                    bindings,
                    materials_block=materials_block,
                    role_label=role_label,
                    student_id=student_id,
                    session_id=session_id,
                )
                return
            if mode == "interview_start":
                yield from iter_interview_mode_tokens(
                    bindings,
                    ctx=ctx,
                    turn_ctx=turn_ctx,
                    question=question,
                    student_id=student_id,
                    role_label=role_label,
                    is_start=True,
                )
                return
            if mode == "interview_turn":
                yield from iter_interview_mode_tokens(
                    bindings,
                    ctx=ctx,
                    turn_ctx=turn_ctx,
                    question=question,
                    student_id=student_id,
                    role_label=role_label,
                    is_start=False,
                )
                return
            if mode == "turn":
                yield from iter_turn_tokens(
                    bindings,
                    ctx=ctx,
                    turn_ctx=turn_ctx,
                    question=question,
                    student_id=student_id,
                    role_label=role_label,
                )
                return
            if mode == "chat":
                yield from iter_chat_tokens(
                    bindings,
                    ctx=ctx,
                    question=question,
                    materials_block=materials_block,
                    role_label=role_label,
                    cancel_event=cancel_event,
                )
                return
        except Exception as exc:
            yield {"type": "answer", "content": f"模拟面试官流水线异常：{exc}"}

    return {
        "usercode": ctx.usercode,
        "model_level": model_level,
        "token_iter": iter_tokens(),
        "cancel": cancel,
    }


def _disabled_stream_context(
    ctx: ChatStreamRunContext, merged_user: Dict[str, Any]
) -> ChatTokenStreamContext:
    """功能开关关闭时的占位流。"""

    def _iter() -> Iterator[Dict[str, str]]:
        yield {
            "type": "answer",
            "content": "模拟面试官功能暂未开放（ROLE005_INTERVIEW_ENABLED=0）。",
        }

    return {
        "usercode": ctx.usercode,
        "model_level": str(merged_user.get("model_level", "mid")),
        "token_iter": _iter(),
        "cancel": lambda: None,
    }
