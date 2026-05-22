"""
ROLE004 兼容入口（实现已迁移至 ``app.session.role.role004``）。

保留本文件路径，避免 ``chat_stream_pipeline`` 等既有 import 失效。
新代码请优先::

    from app.session.role.role004 import stream_chat_service_tokens
"""

from app.session.role.role004 import (
    ChatTokenStreamContext,
    ResumeOptimizeState,
    run_resume_optimize_sync,
    stream_chat_service_tokens,
)

__all__ = [
    "ChatTokenStreamContext",
    "ResumeOptimizeState",
    "run_resume_optimize_sync",
    "stream_chat_service_tokens",
]
