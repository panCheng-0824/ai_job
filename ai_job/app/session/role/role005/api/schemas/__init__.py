"""
ROLE005 API 请求/响应模型（与 server_job schema/interview 对齐）。
"""

from app.session.role.role005.api.schemas.plan import PlanPreviewRequest, PlanPreviewResponse
from app.session.role.role005.api.schemas.turn import TurnRequest, TurnResponse

__all__ = [
    "PlanPreviewRequest",
    "PlanPreviewResponse",
    "TurnRequest",
    "TurnResponse",
]
