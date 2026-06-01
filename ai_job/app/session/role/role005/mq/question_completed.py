"""
ROLE005 — 题完结 MQ 投递（``interview.question.completed``）。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from app.mq.settings import TOPIC_AI_RESULT
from app.session.role.role005.config import ai_job_role, plan_bank_mq_enabled
from app.session.role.role005.mq.envelope import MqEnvelope
from app.session.role.role005.mq.producer import publish_envelope

log = logging.getLogger(__name__)

EVENT_QUESTION_COMPLETED = "interview.question.completed"


def publish_question_completed(
    *,
    student_id: str,
    record_id: str,
    interview_session_id: str,
    question_id: str,
    seq_no: int,
    answer_text: str,
    evaluator_json: Dict[str, Any] | None = None,
    scorer_json: Dict[str, Any] | None = None,
    turn_id: str = "",
) -> tuple[bool, str]:
    """
    单题评估 complete 后投递 MQ，由 server_job 落库并刷新 Redis ctx。

    返回 (是否已发送, 错误说明)。
    """
    if not plan_bank_mq_enabled():
        log.debug("ROLE005_PLAN_BANK_MQ_ENABLED=0，跳过题完结 MQ")
        return False, ""

    tid = (turn_id or str(uuid.uuid4())).strip()
    idem = f"qdone:{record_id}:{question_id}:{seq_no}:{tid}"
    payload = {
        "student_id": (student_id or "").strip(),
        "record_id": (record_id or "").strip(),
        "interview_session_id": (interview_session_id or "").strip(),
        "question_id": (question_id or "").strip(),
        "seq_no": seq_no,
        "answer_text": (answer_text or "").strip(),
        "turn_id": tid,
        "evaluator_json": dict(evaluator_json or {}),
        "scorer_json": dict(scorer_json or {}),
    }
    envelope = MqEnvelope(
        event_type=EVENT_QUESTION_COMPLETED,
        producer=ai_job_role(),
        idempotency_key=idem,
        payload=payload,
    )
    sent = publish_envelope(envelope, topic=TOPIC_AI_RESULT)
    if not sent:
        return False, "MQ 未发送（SDK 未安装或 Broker 不可达）"
    return True, ""
