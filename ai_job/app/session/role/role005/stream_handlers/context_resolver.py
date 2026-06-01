"""
ROLE005 — 解析单轮答题所需的 ContextBundle。
"""

from __future__ import annotations

from typing import Any, Dict

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role005.context_builder import build_dev_context_bundle
from app.session.role.role005.domain.models import ContextBundle
from app.session.role.role005.infra.server_job_client import fetch_context_bundle
from app.session.role.role_util.bindings import GraphBindings


def resolve_context_bundle(
    bindings: GraphBindings,
    *,
    turn_ctx: Dict[str, Any],
    ctx: ChatStreamRunContext,
    student_id: str,
) -> ContextBundle:
    """
    加载面试上下文：优先 server_job，失败则本地 dev 构造。

    生产环境必须能拉到 context-bundle；dev 构造仅用于联调。
    """
    sid = str(turn_ctx.get("interview_session_id") or "").strip()
    if sid:
        bundle = fetch_context_bundle(sid)
        if bundle is not None:
            return bundle
    return build_dev_context_bundle(
        bindings=bindings,
        interview_session_id=sid,
        student_id=student_id,
        context_cards=list(ctx.user_context_cards or []),
        message_context=ctx.user_message_context or "",
        turn_action=str(turn_ctx.get("action") or "start"),
    )
