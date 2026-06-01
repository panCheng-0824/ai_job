"""
ROLE005 — SSE：面试大纲规划预览迭代器。
"""

from __future__ import annotations

import json
from typing import Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role005.domain.models import PlanPreviewResult
from app.session.role.role005.graph.planner_graph import run_plan_preview_sync
from app.session.role.role005.materials import compute_material_hash, extract_target_role
from app.session.role.role005.stream_handlers.plan_preview_summary import (
    format_plan_preview_answer,
)
from app.session.role.role_util.bindings import GraphBindings
from app.session.role.role_util.stream_common import chunk_text


def iter_plan_preview_tokens(
    ctx: ChatStreamRunContext,
    bindings: GraphBindings,
    *,
    materials_block: str,
    role_label: str,
    student_id: str = "",
    session_id: str = "",
) -> Iterator[Dict[str, str]]:
    """
    执行规划图并推送 ``interview_plan_preview`` 事件。

    前端 / server_job 收到后展示摘要，确认后再创建 interview_session。
    """
    mhash = compute_material_hash(materials_block)
    target = extract_target_role(
        materials_block, context_cards=ctx.user_context_cards
    )
    yield {
        "type": "thinking",
        "content": f"【{role_label}·规划】正在生成面试大纲（素材指纹 {mhash[:8]}）…\n",
    }
    preview: PlanPreviewResult = run_plan_preview_sync(
        bindings=bindings,
        materials_block=materials_block,
        material_hash=mhash,
        target_role=target,
        student_id=student_id,
        session_id=session_id,
    )
    payload = {
        "plan": preview.plan.model_dump(),
        "plan_summary": preview.plan_summary.model_dump()
        if preview.plan_summary
        else None,
        "industry_classification": preview.industry_classification.model_dump()
        if preview.industry_classification
        else None,
        "cache_meta": preview.cache_meta,
        "material_hash": preview.material_hash,
        "mq_published": preview.mq_published,
    }
    yield {
        "type": "interview_plan_preview",
        "content": json.dumps(payload, ensure_ascii=False),
    }
    summary = format_plan_preview_answer(preview)
    for piece in chunk_text(summary):
        yield {"type": "answer", "content": piece}
