"""
兼容入口 — 模型已迁至 ``api.schemas`` 子包。
"""

from app.session.role.role005.api.schemas import (
    PlanPreviewRequest,
    PlanPreviewResponse,
    TurnRequest,
    TurnResponse,
)

__all__ = [
    "PlanPreviewRequest",
    "PlanPreviewResponse",
    "TurnRequest",
    "TurnResponse",
]
