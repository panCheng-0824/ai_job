"""
ROLE001 — 图运行时绑定工厂（SSE / 图节点共用）。
"""

from __future__ import annotations

from threading import Event
from typing import Any, Dict

from app.session.role.role001.config import (
    build_plan_execute_role_block,
    resolve_use_structured_return,
    tools_from_user_model,
)
from app.session.role.role001.intent import resolve_intent_mode
from app.session.role.role_util.bindings import GraphBindings


def build_graph_bindings(
    merged_user: Dict[str, Any],
    llm: Any,
    cancel_event: Event,
    *,
    history_block: str = "",
) -> GraphBindings:
    """根据合并后的用户模型构造图运行时绑定（含意图路由所需上下文）。"""
    role_block = build_plan_execute_role_block(merged_user)
    identity = {
        "username": merged_user.get("username", ""),
        "usercode": merged_user.get("usercode", ""),
        "output_format": merged_user.get("output_format", ""),
    }
    tools, tool_map = tools_from_user_model(merged_user)
    use_structured = resolve_use_structured_return(merged_user)
    return GraphBindings(
        llm=llm,
        cancel_event=cancel_event,
        role_block=role_block,
        identity=identity,
        tools=tools,
        tool_map=tool_map,
        use_structured_return=use_structured,
        history_block=history_block,
        intent_mode=resolve_intent_mode(merged_user),
    )
