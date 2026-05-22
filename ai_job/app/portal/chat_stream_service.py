"""SSE 聊天流：组装 chat_stream_pipeline 与取消注册。"""

from typing import Any, Callable, Dict, List, Optional

from app.session.chat_stream_pipeline import build_chat_stream_run_context, iter_chat_stream_sse,iter_chat_stream_sse_by_model
from app.portal import stream_registry


def iter_chat_sse_events(
    session_id: str,
    usercode: str,
    user_model: Dict[str, Any],
    text: str,
    history_turns: List[Dict[str, Any]],
    *,
    use_role_pipeline: bool,
    use_adversarial_harness: bool,
    adversarial_desc: str,
    model_level_fallback: str,
    after_history_mutated: Optional[Callable[[], None]] = None,
    system_prompt_extra: str = "",
    user_display_content: str = "",
    user_message_context: str = "",
    user_context_cards: Optional[List[Dict[str, Any]]] = None,
):
    ctx = build_chat_stream_run_context(
        session_id=session_id,
        usercode=usercode,
        text=text,
        history_turns=history_turns,
        user_model=user_model,
        use_role_pipeline=use_role_pipeline,
        use_adversarial_harness=use_adversarial_harness,
        adversarial_desc=adversarial_desc,
        model_level_fallback=model_level_fallback,
        system_prompt_extra=system_prompt_extra,
        after_history_mutated=after_history_mutated,
        register_stream_canceller=stream_registry.register_stream_canceller,
        clear_stream_canceller_if_same=stream_registry.clear_stream_canceller_if_same,
        safe_cancel=stream_registry.safe_cancel,
        user_display_content=user_display_content,
        user_message_context=user_message_context,
        user_context_cards=user_context_cards,
    )
    # yield from iter_chat_stream_sse(ctx)
    yield from iter_chat_stream_sse_by_model(ctx)

