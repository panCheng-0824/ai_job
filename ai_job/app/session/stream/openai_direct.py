"""
OpenAI 兼容直连流式（通用 chat_service，非角色 LangGraph）。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterator, List

from app.session.chat_service import stream_chat_service_tokens
from app.session.chat_stream_context import ChatStreamRunContext
from app.session.stream.config import HANDLER_OPENAI_DIRECT
from app.session.stream.context_factory import done_meta, persist_user_turn
from app.session.stream.sse_format import sse_chunk, thinking_delta_from_piece


def iter_chat_stream_sse_openai_direct(ctx: ChatStreamRunContext) -> Iterator[str]:
    """``handler_id == openai_direct`` 时走通用流式对话。"""
    cancel_fn: Any = None
    yield sse_chunk("start", json.dumps({"session_id": ctx.session_id}, ensure_ascii=False))
    try:
        if ctx.handler_id != HANDLER_OPENAI_DIRECT:
            yield sse_chunk(
                "error",
                json.dumps(
                    {"detail": f"未实现的 stream_handler: {ctx.handler_id}"},
                    ensure_ascii=False,
                ),
            )
            return

        stream_ctx = stream_chat_service_tokens(
            usercode=ctx.usercode,
            message=ctx.text,
            history=ctx.history_turns,
            temperature=ctx.temperature,
            use_role_pipeline=ctx.use_role_pipeline,
            system_prompt_extra=ctx.system_prompt_extra or None,
        )
        cancel_fn = stream_ctx.get("cancel")
        ctx.register_stream_canceller(ctx.session_id, cancel_fn)

        answer_parts: List[str] = []
        thinking_text = ""
        for token in stream_ctx["token_iter"]:
            piece = token.get("content", "")
            if not piece:
                continue
            if token.get("type") == "thinking":
                delta_piece = thinking_delta_from_piece(thinking_text, piece)
                if not delta_piece:
                    continue
                thinking_text += delta_piece
                yield sse_chunk(
                    "thinking",
                    json.dumps({"content": delta_piece}, ensure_ascii=False),
                )
            else:
                answer_parts.append(piece)
                yield sse_chunk("delta", json.dumps({"content": piece}, ensure_ascii=False))

        answer = "".join(answer_parts).strip()
        thinking_text = thinking_text.strip()
        now = datetime.utcnow().isoformat() + "Z"
        persist_user_turn(ctx, now)
        ctx.history_turns.append({"role": "assistant", "content": answer, "ts": now})
        if ctx.after_history_mutated:
            ctx.after_history_mutated()

        final_payload = {
            "session_id": ctx.session_id,
            "usercode": ctx.usercode,
            "model_level": stream_ctx.get("model_level", ctx.model_level_fallback),
            "use_role_pipeline": ctx.use_role_pipeline,
            "use_adversarial_harness": False,
            "thinking": thinking_text,
            "answer": answer,
            "history": ctx.history_turns,
            **done_meta(ctx),
        }
        yield sse_chunk("done", json.dumps(final_payload, ensure_ascii=False))
    except GeneratorExit:
        ctx.safe_cancel(cancel_fn)
        raise
    except Exception as exc:
        yield sse_chunk("error", json.dumps({"detail": str(exc)}, ensure_ascii=False))
    finally:
        ctx.safe_cancel(cancel_fn)
        ctx.clear_stream_canceller_if_same(ctx.session_id, cancel_fn)


def iter_chat_stream_sse(ctx: ChatStreamRunContext) -> Iterator[str]:
    """按 ``ctx.handler_id`` 派发（对抗 / 直连）。"""
    from app.session.stream.adversarial import iter_chat_stream_sse_adversarial
    from app.session.stream.config import HANDLER_ADVERSARIAL_HARNESS

    if ctx.handler_id == HANDLER_ADVERSARIAL_HARNESS:
        yield from iter_chat_stream_sse_adversarial(ctx)
        return
    yield from iter_chat_stream_sse_openai_direct(ctx)
