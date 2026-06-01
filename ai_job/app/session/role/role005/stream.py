"""
ROLE005 SSE 兼容入口 — 实现已拆分至 ``stream_handlers``。

保留 ``app.session.role.role005.stream`` 导入路径，避免 pipeline 改动。
"""

from app.session.role.role005.stream_handlers import stream_chat_service_tokens
from app.session.role.role005.bindings import build_graph_bindings
from app.session.role.role_util.stream_common import ChatTokenStreamContext

__all__ = [
    "ChatTokenStreamContext",
    "stream_chat_service_tokens",
    "build_graph_bindings",
]
