"""
规划阶段 API 模型 — POST /internal/interview/plan/preview
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.session.role.role005.domain.models import PlanPreviewResult


class PlanPreviewRequest(BaseModel):
    """大纲预览请求：server_job 转发素材，ai_job 执行 Planner 图。"""

    student_id: str = ""
    materials_text: str = ""
    context_cards: List[Dict[str, Any]] = Field(default_factory=list)
    message_context: str = ""
    student_context: str = ""


class PlanPreviewResponse(BaseModel):
    """大纲预览响应：含 success 与结构化 preview。"""

    success: bool = True
    preview: Optional[PlanPreviewResult] = None
    detail: str = ""
