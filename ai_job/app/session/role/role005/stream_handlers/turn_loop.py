"""
ROLE005 — SSE：单轮答题（/turn 同步逻辑的流式展示）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role005.graph.interview_graph import run_interview_turn_sync
from app.session.role.role005.parsing import interviewer_display_text
from app.session.role.role005.stream_handlers.context_resolver import resolve_context_bundle
from app.session.role.role_util.bindings import GraphBindings
from app.session.role.role_util.stream_common import chunk_text


def iter_turn_tokens(
    bindings: GraphBindings,
    *,
    ctx: ChatStreamRunContext,
    turn_ctx: Dict[str, Any],
    question: str,
    student_id: str,
    role_label: str,
) -> Iterator[Dict[str, str]]:
    """
    执行答题图并推送 progress / turn / answer 事件。

    注意：业务落库在 server_job ``POST /turn``；本路径为聊天 SSE 联调入口。
    """
    action = str(turn_ctx.get("action") or "answer").strip()
    payload = turn_ctx.get("payload") if isinstance(turn_ctx.get("payload"), dict) else {}

    bundle = resolve_context_bundle(
        bindings,
        turn_ctx=turn_ctx,
        ctx=ctx,
        student_id=student_id,
    )
    yield {
        "type": "thinking",
        "content": (
            f"【{role_label}·答题】session={bundle.session.interview_session_id} "
            f"action={action} phase={bundle.session.phase}\n"
        ),
    }

    turn_result = run_interview_turn_sync(
        bindings=bindings,
        context=bundle,
        turn_action=action,
        turn_payload=payload,
        user_query=question,
    )
    progress = {
        "interview_session_id": turn_result.interview_session_id,
        "phase": turn_result.phase,
        "current_question_index": turn_result.current_question_index,
        "action": turn_result.action,
    }
    yield {
        "type": "interview_progress",
        "content": json.dumps(progress, ensure_ascii=False),
    }

    interviewer = turn_result.interviewer_output or {}
    display = turn_result.final_answer_text or interviewer_display_text(interviewer)
    yield {
        "type": "interview_turn",
        "content": json.dumps(
            {
                "interviewer": interviewer,
                "evaluator": turn_result.evaluator_output,
                "scorer": turn_result.scorer_output,
                "turn_result": turn_result.model_dump(),
            },
            ensure_ascii=False,
        ),
    }
    for piece in chunk_text(display):
        if bindings.cancel_event.is_set():
            break
        yield {"type": "answer", "content": piece}
