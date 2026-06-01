"""
按 usercode 派发角色专用流式实现（LangGraph / 结构化 SSE）。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterator, List

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.stream.context_factory import done_meta, persist_user_turn
from app.session.stream.role_registry import resolve_role_stream
from app.session.stream.sse_format import sse_chunk
from app.session.stream.token_forward import collect_forward_tokens

logger = logging.getLogger(__name__)


def iter_chat_stream_sse_by_model(ctx: ChatStreamRunContext) -> Iterator[str]:
    """按 ``ctx.usercode`` 选择角色流入口，转发 token 并写 history。"""
    cancel_fn: Any = None
    yield sse_chunk("start", json.dumps({"session_id": ctx.session_id}, ensure_ascii=False))
    try:
        role_stream = resolve_role_stream(ctx.usercode)
        stream_ctx = role_stream(ctx)
        cancel_fn = stream_ctx.get("cancel")
        ctx.register_stream_canceller(ctx.session_id, cancel_fn)

        sse_iter, agg = collect_forward_tokens(ctx, stream_ctx["token_iter"])
        yield from sse_iter

        answer = "".join(agg["answer_parts"]).strip()
        thinking_text = str(agg["thinking_text"]).strip()
        job_recommend_payload = agg.get("job_recommend")
        resume_render_payload = agg.get("resume_render")

        now = datetime.utcnow().isoformat() + "Z"
        persist_user_turn(ctx, now)
        assistant_turn: Dict[str, Any] = {"role": "assistant", "content": answer, "ts": now}
        if job_recommend_payload:
            assistant_turn["job_recommend"] = job_recommend_payload
        if resume_render_payload:
            assistant_turn["resume_render"] = resume_render_payload
        ctx.history_turns.append(assistant_turn)
        if ctx.history_turns:
            last = ctx.history_turns[-1]
            if last.get("role") == "assistant":
                if resume_render_payload and not last.get("resume_render"):
                    last["resume_render"] = resume_render_payload
                if job_recommend_payload and not last.get("job_recommend"):
                    last["job_recommend"] = job_recommend_payload
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
        if job_recommend_payload:
            final_payload["job_recommend"] = job_recommend_payload
        if resume_render_payload:
            final_payload["resume_render"] = resume_render_payload
        yield sse_chunk("done", json.dumps(final_payload, ensure_ascii=False))
    except GeneratorExit:
        ctx.safe_cancel(cancel_fn)
        raise
    except Exception as exc:
        logger.exception("role stream failed usercode=%s", ctx.usercode)
        yield sse_chunk("error", json.dumps({"detail": str(exc)}, ensure_ascii=False))
    finally:
        ctx.safe_cancel(cancel_fn)
        ctx.clear_stream_canceller_if_same(ctx.session_id, cancel_fn)
