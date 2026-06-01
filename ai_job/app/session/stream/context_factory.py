"""
构建 ChatStreamRunContext 与 history 持久化辅助。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.stream.config import resolve_stream_handler_and_options
from app.session.user_turn_context import append_user_turn_to_history


def persist_user_turn(ctx: ChatStreamRunContext, now: str) -> None:
    """将本轮用户消息写入 history_turns（含 context_cards 等扩展字段）。"""
    display = (ctx.user_display_content or "").strip()
    if not display and not ctx.user_context_cards and not ctx.user_message_context:
        display = (ctx.text or "").strip()
    append_user_turn_to_history(
        ctx.history_turns,
        ts=now,
        display_content=display,
        message_context=ctx.user_message_context,
        context_cards=ctx.user_context_cards,
    )


def build_chat_stream_run_context(
    *,
    session_id: str,
        student_id: str,
    usercode: str,
    text: str,
    history_turns: List[Dict[str, Any]],
    user_model: Dict[str, Any],
    use_role_pipeline: bool,
    use_adversarial_harness: bool,
    adversarial_desc: str,
    model_level_fallback: str,
    system_prompt_extra: str,
    after_history_mutated: Optional[Callable[[], None]],
    register_stream_canceller: Callable[[str, Any], None],
    clear_stream_canceller_if_same: Callable[[str, Any], None],
    safe_cancel: Callable[[Any], None],
    user_display_content: str = "",
    user_message_context: str = "",
    user_context_cards: Optional[List[Dict[str, Any]]] = None,
) -> ChatStreamRunContext:
    """组装单次 SSE 请求的运行时上下文（handler、温度、回调等）。"""
    handler_id, opts = resolve_stream_handler_and_options(
        user_model,
        use_adversarial_harness=use_adversarial_harness,
        use_role_pipeline=use_role_pipeline,
    )
    return ChatStreamRunContext(
        session_id=session_id,
        student_id=student_id,
        usercode=usercode,
        user_model=user_model,
        text=text,
        history_turns=history_turns,
        handler_id=handler_id,
        use_role_pipeline=bool(opts["use_role_pipeline"]),
        use_adversarial_harness=use_adversarial_harness,
        adversarial_max_rounds=int(opts["adversarial_max_rounds"]),
        adversarial_desc=adversarial_desc,
        model_level_fallback=model_level_fallback,
        system_prompt_extra=system_prompt_extra,
        temperature=float(opts["temperature"]),
        after_history_mutated=after_history_mutated,
        register_stream_canceller=register_stream_canceller,
        clear_stream_canceller_if_same=clear_stream_canceller_if_same,
        safe_cancel=safe_cancel,
        user_display_content=user_display_content,
        user_message_context=user_message_context,
        user_context_cards=list(user_context_cards or []),
    )


def done_meta(ctx: ChatStreamRunContext) -> Dict[str, Any]:
    """done 事件附加元数据，便于排查 handler 与对抗配置。"""
    return {
        "stream_handler": ctx.handler_id,
        "adversarial_max_rounds": ctx.adversarial_max_rounds,
    }
