"""
ROLE001 SSE 兼容入口 — 实现已拆分至 ``stream_handlers``。
"""

from app.session.role.role001.bindings_factory import build_graph_bindings
from app.session.role.role001.stream_handlers import stream_chat_service_tokens
from app.session.role.role_util.stream_common import ChatTokenStreamContext

__all__ = [
    "ChatTokenStreamContext",
    "stream_chat_service_tokens",
    "build_graph_bindings",
]
