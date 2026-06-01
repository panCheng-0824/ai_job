"""
ROLE005 — 答题图：面试官节点（只提问，不评分）。
"""

from __future__ import annotations

from app.session.role.role005.agents.clarifier import run_clarifier_agent
from app.session.role.role005.agents.interviewer import run_interviewer_agent
from app.session.role.role005.domain.state import InterviewGraphState
from app.session.role.role005.graph.nodes._state_helpers import current_question_id, student_text
from app.session.role.role005.parsing import interviewer_display_text
from app.session.role.role_util.bindings import GraphBindings, is_cancelled


def make_interviewer_node(bindings: GraphBindings):
    """
    生成面试官 JSON 输出。

    clarify 动作先走 Clarifier 再包装为 interviewer JSON，保证不泄露参考答案。
    """

    def node(state: InterviewGraphState) -> dict:
        if is_cancelled(bindings) or not state.context:
            return {"error": "缺少面试上下文"}
        text = student_text(state)

        if state.turn_action == "clarify" and text:
            clarify = run_clarifier_agent(
                bindings, bundle=state.context, student_text=text
            )
            out = {
                "action": "clarify",
                "question_id": current_question_id(state),
                "clarify_text": clarify,
                "question_text": clarify,
            }
            return {
                "interviewer_json": out,
                "clarifier_text": clarify,
                "final_answer": interviewer_display_text(out),
            }

        out, err = run_interviewer_agent(
            bindings,
            bundle=state.context,
            turn_action=state.turn_action,
            student_text=text,
        )
        if err:
            return {"error": err, "final_answer": f"面试官生成失败：{err}"}
        return {
            "interviewer_json": out,
            "final_answer": interviewer_display_text(out),
        }

    return node
