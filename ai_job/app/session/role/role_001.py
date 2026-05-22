"""
ROLE001 兼容入口（实现已迁移至 ``app.session.role.role001``）。

保留本文件路径，避免 ``chat_stream_pipeline`` 等既有 import 失效。
新代码请优先::

    from app.session.role.role001 import stream_chat_service_tokens
"""

from app.session.role.role001 import (
    ChatTokenStreamContext,
    JobPlanExecuteState,
    run_job_plan_execute_sync,
    stream_chat_service_tokens,
)

__all__ = [
    "ChatTokenStreamContext",
    "JobPlanExecuteState",
    "run_job_plan_execute_sync",
    "stream_chat_service_tokens",
]
