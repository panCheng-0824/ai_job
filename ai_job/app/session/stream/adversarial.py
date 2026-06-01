"""
对抗 harness 流式分支（非 token 流，一次算完伪流式下发）。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.stream.context_factory import done_meta, persist_user_turn
from app.session.stream.sse_format import sse_chunk
from app.skills.adversarial_harness import run_adversarial_harness


def iter_chat_stream_sse_adversarial(ctx: ChatStreamRunContext) -> Iterator[str]:
    cancel_fn = None
    yield sse_chunk("start", json.dumps({"session_id": ctx.session_id}, ensure_ascii=False))
    try:
        harness_result = run_adversarial_harness(
            role_ref=ctx.usercode,
            adversary_desc=ctx.adversarial_desc,
            question=ctx.text,
            max_rounds=ctx.adversarial_max_rounds,
        )
        answer = str(harness_result.get("final_answer", "")).strip()
        if answer:
            yield sse_chunk("delta", json.dumps({"content": answer}, ensure_ascii=False))

        now = datetime.utcnow().isoformat() + "Z"
        persist_user_turn(ctx, now)
        ctx.history_turns.append({"role": "assistant", "content": answer, "ts": now})
        if ctx.after_history_mutated:
            ctx.after_history_mutated()

        final_payload = {
            "session_id": ctx.session_id,
            "usercode": ctx.usercode,
            "model_level": ctx.model_level_fallback,
            "use_role_pipeline": ctx.use_role_pipeline,
            "use_adversarial_harness": True,
            "thinking": "",
            "adversarial_review": str(harness_result.get("final_review", "")),
            "adversarial_rounds_used": int(harness_result.get("rounds_used", 0)),
            "adversarial_history": harness_result.get("history", []),
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
