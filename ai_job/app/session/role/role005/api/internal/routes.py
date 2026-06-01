"""
ROLE005 内部 HTTP 路由注册（仅路径映射，逻辑在 handlers/）。
"""

from __future__ import annotations

from fastapi import APIRouter, Header

from app.session.role.role005.api.handlers import handle_interview_turn, handle_plan_preview
from app.session.role.role005.api.schemas import (
    PlanPreviewRequest,
    PlanPreviewResponse,
    TurnRequest,
    TurnResponse,
)

router = APIRouter(prefix="/api/internal/interview", tags=["interview-internal"])


@router.post("/plan/preview", response_model=PlanPreviewResponse)
def internal_plan_preview(
    body: PlanPreviewRequest,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
):
    """server_job 转发：生成或命中缓存的面试大纲预览。"""
    return handle_plan_preview(body, x_service_token=x_service_token)


@router.post("/turn", response_model=TurnResponse)
def internal_interview_turn(
    body: TurnRequest,
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
):
    """server_job 转发：单轮 LangGraph（幂等与落库在 server_job）。"""
    return handle_interview_turn(body, x_service_token=x_service_token)
