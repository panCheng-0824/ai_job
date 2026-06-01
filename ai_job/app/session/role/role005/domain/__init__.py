"""
ROLE005 领域层 — Pydantic 契约与 LangGraph 状态 dataclass。

与 server_job ``resources/schema/interview/`` JSON Schema 保持字段一致。
"""

from app.session.role.role005.domain.models import (
    ContextBundle,
    InterviewPlan,
    InterviewReport,
    InterviewSessionSnapshot,
    PlanPreviewResult,
    PlanSummary,
    QuestionItem,
    TurnResult,
)

__all__ = [
    "ContextBundle",
    "InterviewPlan",
    "InterviewReport",
    "InterviewSessionSnapshot",
    "PlanPreviewResult",
    "PlanSummary",
    "QuestionItem",
    "TurnResult",
]
