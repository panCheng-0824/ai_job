"""
ROLE005 — RocketMQ 生产者（ai_job_a / ai_job_b / server_job 投递异步任务）。
"""

from __future__ import annotations

import json
import logging

from app.mq.client import send_json
from app.mq.settings import (
    TOPIC_AI_RESULT,
    TOPIC_AI_TASK,
    producer_group_for_role,
    rocketmq_proxy_grpc_endpoint,
)
from app.session.role.role005.config import ai_job_role
from app.session.role.role005.mq.envelope import MqEnvelope

log = logging.getLogger(__name__)


def publish_envelope(envelope: MqEnvelope, *, topic: str = TOPIC_AI_TASK) -> bool:
    """
    发送 MQ 消息（5.x SDK 经 Proxy gRPC，见 ``ROCKETMQ_PROXY_GRPC_ENDPOINT``）。
    """
    body = envelope.model_dump()
    role = ai_job_role()
    group = producer_group_for_role(role)
    sent = send_json(topic, body, group=group)
    log.info(
        "MQ 投递 topic=%s proxy_grpc=%s group=%s role=%s event=%s message_id=%s sent=%s",
        topic,
        rocketmq_proxy_grpc_endpoint(),
        group,
        role,
        envelope.event_type,
        envelope.message_id,
        sent,
    )
    if not sent:
        log.debug("MQ body=%s", json.dumps(body, ensure_ascii=False)[:2000])
    return sent
