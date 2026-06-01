"""
内部 API — 单轮答题 /turn 处理逻辑。
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from app.session.role.role005.api.auth import verify_service_token
from app.session.role.role005.api.bindings_factory import create_internal_graph_bindings
from app.session.role.role005.api.schemas.turn import TurnRequest, TurnResponse
from app.session.role.role005.config import interview_enabled
from app.session.role.role005.graph.interview_graph import run_interview_turn_sync

log = logging.getLogger(__name__)


def handle_interview_turn(
    body: TurnRequest,
    *,
    x_service_token: str | None,
) -> TurnResponse:
    """执行答题主图；不在此写 MySQL。"""
    if not interview_enabled():
        raise HTTPException(status_code=503, detail="ROLE005 面试功能未启用")
    verify_service_token(x_service_token)

    action = (body.action or "answer").strip()
    try:
        bindings = create_internal_graph_bindings()
        result = run_interview_turn_sync(
            bindings=bindings,
            context=body.context_bundle,
            turn_action=action,
            turn_payload=body.payload,
            user_query=body.user_query,
        )
        return TurnResponse(success=True, result=result)
    except Exception as exc:
        sid = body.context_bundle.session.interview_session_id
        log.exception("interview/turn 失败 session=%s", sid)
        return TurnResponse(success=False, detail=str(exc))
