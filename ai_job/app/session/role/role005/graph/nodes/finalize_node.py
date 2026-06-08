"""
ROLE005 — 答题图：收尾节点，组装 TurnResult 供 server_job 事务写入。
"""

from __future__ import annotations

import json

from app.session.role.role005.domain.models import TurnResult
from app.session.role.role005.domain.state import InterviewGraphState
from app.session.role.role_util.bindings import GraphBindings, is_cancelled


def make_finalize_turn_node(bindings: GraphBindings):
    """将图内 Agent 产出封装为 TurnResult（不写 MySQL）。"""

    def node(state: InterviewGraphState) -> dict:
        if is_cancelled(bindings) or not state.context:
            return {}
        ctx = state.context
        sid = ctx.session.interview_session_id

        turn_result = TurnResult(
            interview_session_id=sid,
            action=state.turn_action,
            phase=ctx.session.phase,
            current_question_index=ctx.session.current_question_index,
            interviewer_output=state.interviewer_json,
            evaluator_output=state.evaluator_json,
            scorer_output=state.scorer_json,
            session_delta={
                "evaluator_status": state.evaluator_json.get("status"),
            },
            final_answer_text=state.final_answer,
        )
        payload = turn_result.model_dump()
        answer = json.dumps(
            {"interviewer": state.interviewer_json, "turn_result": payload},
            ensure_ascii=False,
            indent=2,
        )
        return {"turn_result": payload, "final_answer": answer}

    return node
