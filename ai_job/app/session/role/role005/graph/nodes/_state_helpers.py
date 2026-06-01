"""
ROLE005 图节点 — 从 InterviewGraphState 提取常用字段。
"""

from __future__ import annotations

from app.session.role.role005.domain.state import InterviewGraphState


def student_text(state: InterviewGraphState) -> str:
    """本轮学生输入：优先 payload.answer_text，否则 user_query。"""
    payload = state.turn_payload or {}
    return str(payload.get("answer_text") or state.user_query or "").strip()


def current_question_id(state: InterviewGraphState) -> str:
    """当前题在大纲中的 id；越界时返回空串。"""
    if not state.context:
        return ""
    idx = state.context.session.current_question_index
    questions = state.context.plan.questions
    if 0 <= idx < len(questions):
        return questions[idx].id
    return ""
