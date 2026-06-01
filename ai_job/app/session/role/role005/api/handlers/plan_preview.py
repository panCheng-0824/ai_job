"""
内部 API — 大纲规划预览处理逻辑。
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from app.session.role.role005.api.auth import verify_service_token
from app.session.role.role005.api.bindings_factory import create_internal_graph_bindings
from app.session.role.role005.api.schemas.plan import PlanPreviewRequest, PlanPreviewResponse
from app.session.role.role005.config import interview_enabled
from app.session.role.role005.graph.planner_graph import run_plan_preview_sync
from app.session.role.role005.materials import (
    build_interview_materials_block,
    compute_material_hash,
    extract_target_role,
)

log = logging.getLogger(__name__)


def handle_plan_preview(
    body: PlanPreviewRequest,
    *,
    x_service_token: str | None,
) -> PlanPreviewResponse:
    """同步执行规划图，返回 PlanPreviewResult。"""
    if not interview_enabled():
        raise HTTPException(status_code=503, detail="ROLE005 面试功能未启用")
    verify_service_token(x_service_token)

    materials = body.materials_text.strip() or build_interview_materials_block(
        message_context=body.message_context,
        context_cards=body.context_cards,
    )
    if not materials:
        raise HTTPException(status_code=400, detail="缺少简历/岗位素材")

    mhash = compute_material_hash(materials)
    target = extract_target_role(
        materials, context_cards=body.context_cards
    )
    try:
        bindings = create_internal_graph_bindings()
        preview = run_plan_preview_sync(
            bindings=bindings,
            materials_block=materials,
            material_hash=mhash,
            target_role=target,
            student_context=body.student_context,
            student_id=body.student_id,
        )
        return PlanPreviewResponse(success=True, preview=preview)
    except Exception as exc:
        log.exception("plan/preview 失败")
        return PlanPreviewResponse(success=False, detail=str(exc))
