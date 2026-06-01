"""
ROLE005 — 开发/联调用的 ContextBundle 构造。

使用场景
--------
- server_job ``GET /internal/interview/sessions/{id}/context-bundle`` 不可用时；
- 聊天 SSE 联调尚未创建正式 interview_session 时。

正式生产流量必须由 server_job 提供上下文，禁止依赖本模块推导业务状态。
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.session.role.role005.domain.models import (
    ContextBundle,
    InterviewPlan,
    InterviewSessionSnapshot,
    QuestionItem,
)
from app.session.role.role005.graph.planner_graph import run_plan_preview_sync
from app.session.role.role005.materials import (
    build_interview_materials_block,
    build_snapshots_from_cards,
    compute_material_hash,
    extract_target_role,
)
from app.session.role.role_util.bindings import GraphBindings


def build_dev_context_bundle(
    *,
    bindings: GraphBindings,
    interview_session_id: str,
    student_id: str,
    context_cards: List[Dict[str, Any]],
    message_context: str,
    plan: Optional[InterviewPlan] = None,
    turn_action: str = "start",
) -> ContextBundle:
    """
    本地构造面试上下文：若无现成 plan 则先跑规划图生成大纲。

    仅用于 server_job 接口不可用时的 SSE 联调。
    """
    materials = build_interview_materials_block(
        message_context=message_context,
        context_cards=context_cards,
    )
    mhash = compute_material_hash(materials)
    target = extract_target_role(materials, context_cards=context_cards)
    job_snap, company_snap, resume_snap = build_snapshots_from_cards(context_cards)

    if plan is None:
        preview = run_plan_preview_sync(
            bindings=bindings,
            materials_block=materials,
            material_hash=mhash,
            target_role=target,
        )
        plan = preview.plan

    sid = (interview_session_id or "").strip() or f"isess_{uuid.uuid4().hex[:12]}"
    phase = "self_intro" if turn_action == "start" else "question"
    session = InterviewSessionSnapshot(
        interview_session_id=sid,
        student_id=student_id or "dev_student",
        plan_id=plan.plan_id,
        plan_version=plan.version,
        status="in_progress",
        phase=phase,
        current_question_index=0 if turn_action == "start" else 0,
        snapshots={
            "job": job_snap,
            "company": company_snap,
            "resume": resume_snap,
        },
    )
    return ContextBundle(session=session, plan=plan, student_profile={})


def default_stub_plan(target_role: str = "技术岗位") -> InterviewPlan:
    """无 LLM 时的最小兜底大纲（仅测试）。"""
    return InterviewPlan(
        plan_id=f"plan_stub_{uuid.uuid4().hex[:8]}",
        version=1,
        target_role=target_role,
        questions=[
            QuestionItem(
                id="q1",
                text="请做一个简短的自我介绍，并说明你最擅长的一项技术。",
                dimensions=["表达", "技术深度"],
                thinking_hint="控制在 2 分钟内",
                timeout_seconds=300,
                reference_answer="（内部参考）",
            ),
        ],
    )
