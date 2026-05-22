"""
角色流水线 — LangGraph 运行时依赖绑定（多角色共用）。
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Any, Dict, List

from langchain_core.tools import BaseTool


@dataclass(frozen=True)
class GraphBindings:
    """
    编译角色图时的只读依赖集合。

    各角色节点通过 ``bindings.llm``、``bindings.role_block`` 等访问共享资源；
    ``history_block`` / ``intent_mode`` 供入口意图路由使用（角色可忽略未用字段）。
    """

    llm: Any
    cancel_event: Event
    role_block: str
    identity: Dict[str, Any]
    tools: List[BaseTool]
    tool_map: Dict[str, BaseTool]
    use_structured_return: bool = False
    history_block: str = ""
    intent_mode: str = "auto"


def is_cancelled(bindings: GraphBindings) -> bool:
    """客户端是否已请求中止当前流式会话。"""
    return bindings.cancel_event.is_set()
