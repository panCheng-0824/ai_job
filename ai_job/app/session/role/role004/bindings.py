"""
ROLE004 图运行时绑定与状态 coercion。
"""

from __future__ import annotations

from typing import Any

from app.session.role.role004.resume_templates import DEFAULT_TEMPLATE_ID, get_template
from app.session.role.role004.state import ResumeOptimizeState

__all__ = ["coerce_graph_state"]


def coerce_graph_state(question: str, data: Any) -> ResumeOptimizeState:
    """将 LangGraph ``invoke`` 返回值统一为 ``ResumeOptimizeState``。"""
    if isinstance(data, ResumeOptimizeState):
        return data
    if isinstance(data, dict):
        intent_raw = str(data.get("intent") or "resume_advise").strip()
        intent = "resume_generate" if intent_raw == "resume_generate" else "resume_advise"
        resume_content = data.get("resume_content")
        if not isinstance(resume_content, dict):
            resume_content = {}
        tid = str(data.get("template_id") or DEFAULT_TEMPLATE_ID).strip()
        return ResumeOptimizeState(
            question=str(data.get("question") or question),
            user_query=str(data.get("user_query") or ""),
            student_context=str(data.get("student_context") or ""),
            materials_block=str(data.get("materials_block") or ""),
            template_id=get_template(tid).id,
            intent=intent,
            final_answer=str(data.get("final_answer") or ""),
            resume_content=dict(resume_content),
        )
    raise TypeError(f"无法解析 LangGraph 状态: {type(data)!r}")
