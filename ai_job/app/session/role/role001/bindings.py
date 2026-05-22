"""
ROLE001 图运行时绑定与状态 coercion。
"""

from __future__ import annotations

from typing import Any

from app.session.role.role001.state import JobPlanExecuteState
from app.session.role.role_util.bindings import GraphBindings, is_cancelled

__all__ = ["GraphBindings", "is_cancelled", "coerce_graph_state"]


def coerce_graph_state(question: str, data: Any) -> JobPlanExecuteState:
    """将 LangGraph ``invoke`` 返回值统一为 ``JobPlanExecuteState``。"""
    if isinstance(data, JobPlanExecuteState):
        return data
    if isinstance(data, dict):
        intent_raw = str(data.get("intent") or "career_consult").strip()
        intent = "job_recommend" if intent_raw == "job_recommend" else "career_consult"
        return JobPlanExecuteState(
            question=str(data.get("question") or question),
            user_query=str(data.get("user_query") or ""),
            student_context=str(data.get("student_context") or ""),
            intent=intent,
            plan=list(data.get("plan") or []),
            step_index=int(data.get("step_index", 0)),
            observations=list(data.get("observations") or []),
            structured_payload=str(data.get("structured_payload") or ""),
            final_answer=str(data.get("final_answer") or ""),
            job_recommend=dict(data.get("job_recommend") or {}),
        )
    raise TypeError(f"无法解析 LangGraph 状态: {type(data)!r}")
