"""
答题阶段 API 模型 — POST /internal/interview/turn
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.session.role.role005.domain.models import ContextBundle, TurnResult


class TurnRequest(BaseModel):
    """
    单轮 turn 请求。

    context_bundle 由 server_job 在幂等/加锁后组装，ai_job 只做 LangGraph 推理。
    """

    context_bundle: ContextBundle
    turn_id: str = ""
    action: str = "answer"
    payload: Dict[str, Any] = Field(default_factory=dict)
    user_query: str = ""


class TurnResponse(BaseModel):
    """单轮 turn 响应：result 供 server_job 事务落库。"""

    success: bool = True
    result: Optional[TurnResult] = None
    detail: str = ""
