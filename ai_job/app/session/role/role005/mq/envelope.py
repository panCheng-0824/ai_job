"""
ROLE005 — RocketMQ 统一消息信封。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field


class MqEnvelope(BaseModel):
    """跨服务 MQ 消息标准结构。"""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    producer: str = "ai_job_a"
    occurred_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    idempotency_key: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
