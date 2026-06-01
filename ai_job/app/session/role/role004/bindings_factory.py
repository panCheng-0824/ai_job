"""
ROLE004 — 图运行时绑定工厂。
"""

from __future__ import annotations

from threading import Event
from typing import Any, Dict

from app.session.role.role004.intent import resolve_resume_intent_mode
from app.session.role.role_util.bindings import GraphBindings
from app.session.role.role_util.config import build_role_block, tools_from_user_model


def build_graph_bindings(
    merged_user: Dict[str, Any],
    llm: Any,
    cancel_event: Event,
    *,
    history_block: str = "",
) -> GraphBindings:
    role_block = build_role_block(merged_user)
    identity = {
        "username": merged_user.get("username", ""),
        "usercode": merged_user.get("usercode", ""),
        "output_format": merged_user.get("output_format", ""),
    }
    tools, tool_map = tools_from_user_model(merged_user)
    return GraphBindings(
        llm=llm,
        cancel_event=cancel_event,
        role_block=role_block,
        identity=identity,
        tools=tools,
        tool_map=tool_map,
        use_structured_return=False,
        history_block=history_block,
        intent_mode=resolve_resume_intent_mode(merged_user),
    )
