"""
ROLE005 SSE 流式处理子模块（由 ``stream.py`` 统一入口调用）。

不持有业务状态；进度真相在 server_job MySQL。
"""

from app.session.role.role005.stream_handlers.entry import stream_chat_service_tokens

__all__ = ["stream_chat_service_tokens"]
