"""
ROLE005 — RocketMQ 消费者（ai_job_b Worker）。

消费 ``interview_ai_task``，完成后生产 ``interview_ai_result``。
"""

from __future__ import annotations

import json
import logging

from app.mq.settings import CONSUMER_GROUP_AI_JOB_B, TOPIC_AI_RESULT
from app.session.role.role005.mq.envelope import MqEnvelope
from app.session.role.role005.mq.producer import publish_envelope

log = logging.getLogger(__name__)


def handle_task_envelope(envelope: MqEnvelope) -> None:
    """
    处理单条异步 AI 任务。

    按 event_type 分发：reflection / plan.generate / report.generate 等。
    """
    event = (envelope.event_type or "").strip()
    log.info(
        "Worker 收到任务 event=%s idempotency=%s trace=%s",
        event,
        envelope.idempotency_key,
        envelope.trace_id,
    )
    if event.endswith(".reflection.request") or event == "interview.reflection.request":
        _handle_reflection_request(envelope)
        return
    if event.endswith(".plan.generate") or event == "interview.plan.generate":
        _handle_plan_generate(envelope)
        return
    log.warning("未识别的 event_type=%s，忽略", event)


def handle_task_json(raw: str) -> None:
    """解析 JSON 字符串并分发。"""
    try:
        data = json.loads(raw or "{}")
        envelope = MqEnvelope.model_validate(data)
    except Exception as exc:
        log.warning("无法解析 MQ 任务消息: %s", exc)
        return
    handle_task_envelope(envelope)


def _handle_reflection_request(envelope: MqEnvelope) -> None:
    """Reflection 占位：产出 result 消息供 server_job 入库。"""
    result = MqEnvelope(
        event_type="interview.reflection.result",
        producer="ai_job_b",
        idempotency_key=envelope.idempotency_key,
        trace_id=envelope.trace_id,
        payload={
            "status": "stub",
            "message": "Reflection Worker 待实现",
            "request_payload": envelope.payload,
        },
    )
    publish_envelope(result, topic=TOPIC_AI_RESULT)


def _handle_plan_generate(envelope: MqEnvelope) -> None:
    """异步大纲生成占位。"""
    result = MqEnvelope(
        event_type="interview.plan.result",
        producer="ai_job_b",
        idempotency_key=envelope.idempotency_key,
        trace_id=envelope.trace_id,
        payload={
            "status": "stub",
            "message": "异步规划待对接 Planner 图",
            "request_payload": envelope.payload,
        },
    )
    publish_envelope(result, topic=TOPIC_AI_RESULT)
