"""
ROLE005 — 大纲题库 MQ 投递。

规划图完成后将 ``InterviewPlan`` + ``PlanSummary`` 打包为 ``interview.plan.result``，
由 server_job 消费并写入 V2 关系表（``interview_plan_basics`` 及题目子表）。
"""

from __future__ import annotations

import logging

import uuid_utils

from app.mq.settings import TOPIC_AI_RESULT
from app.session.role.role005.config import ai_job_role, plan_bank_mq_enabled
from app.session.role.role005.domain.models import (
    InterviewPlan,
    PlanIndustryClassification,
    PlanSummary,
)
from app.session.role.role005.mq.envelope import MqEnvelope
from app.session.role.role005.mq.producer import publish_envelope

log = logging.getLogger(__name__)

EVENT_PLAN_RESULT = "interview.plan.result"


def build_plan_bank_payload(
    *,
    student_id: str,
    session_id: str,
    material_hash: str,
    target_role: str,
    plan: InterviewPlan,
    plan_summary: PlanSummary | None,
    industry_classification: PlanIndustryClassification | None = None,
    cache_meta: dict | None = None,
) -> dict:
    """组装 server_job 落库用的 result payload。"""
    industry_id = (plan.industry_category_id or "").strip()
    if not industry_id and industry_classification is not None:
        industry_id = industry_classification.industry_category_id
    return {
        "status": "ok",
        "student_id": (student_id or "").strip(),
        "session_id": (session_id or "").strip(),
        "material_hash": material_hash,
        "target_role": target_role or plan.target_role,
        "industry_category_id": industry_id,
        "industry_classification": industry_classification.model_dump()
        if industry_classification
        else {},
        "cache_meta": dict(cache_meta or {}),
        "plan": plan.model_dump(),
        "plan_summary": plan_summary.model_dump() if plan_summary else {},
    }


def publish_plan_bank_result(
    *,
    student_id: str,
    material_hash: str,
    target_role: str,
    plan: InterviewPlan,
    plan_summary: PlanSummary | None,
    industry_classification: PlanIndustryClassification | None = None,
    cache_meta: dict | None = None,
) -> tuple[bool, str]:
    """
    投递 ``interview.plan.result`` 至 ``interview_ai_result`` Topic。

    返回 (是否已发送, 错误说明)。未启用 MQ 或 SDK 不可用时 sent=False 且 error 为空（仅日志）。
    """
    if not plan_bank_mq_enabled():
        log.debug("ROLE005_PLAN_BANK_MQ_ENABLED=0，跳过大纲题库 MQ")
        return False, ""

    idem = f"plan:{plan.plan_id}:{plan.version}:{material_hash or plan.source_material_hash}"
    # idem=f"plan_{uuid_utils.UUID}"
    payload = build_plan_bank_payload(
        student_id=student_id,
        session_id=student_id,
        material_hash=material_hash,
        target_role=target_role,
        plan=plan,
        plan_summary=plan_summary,
        industry_classification=industry_classification,
        cache_meta=cache_meta,
    )
    envelope = MqEnvelope(
        event_type=EVENT_PLAN_RESULT,
        producer=ai_job_role(),
        idempotency_key=idem,
        payload=payload,
    )
    sent = publish_envelope(envelope, topic=TOPIC_AI_RESULT)
    if not sent:
        return False, "MQ 未发送（SDK 未安装或 Broker 不可达）"
    return True, ""
