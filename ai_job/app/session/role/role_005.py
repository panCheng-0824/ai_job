"""
ROLE005 兼容入口（实现已迁移至 ``app.session.role.role005``）。

保留本文件路径，避免 ``chat_stream_pipeline`` 等既有 import 失效。
"""

from app.session.role.role005 import (
    ChatTokenStreamContext,
    run_interview_turn_sync,
    run_plan_preview_sync,
    stream_chat_service_tokens,
)

__all__ = [
    "ChatTokenStreamContext",
    "run_plan_preview_sync",
    "run_interview_turn_sync",
    "stream_chat_service_tokens",
]
