"""
会话 SSE 流层 — 按 usercode / handler_id 分发，与角色实现解耦。

层次
----
- ``config``：handler 解析与运行时参数
- ``role_registry``：usercode → 角色 stream 入口
- ``token_forward``：Token → SSE 事件
- ``by_model`` / ``openai_direct`` / ``adversarial``：三种派发路径
- ``context_factory``：构建 ChatStreamRunContext
"""

from app.session.stream.adversarial import iter_chat_stream_sse_adversarial
from app.session.stream.by_model import iter_chat_stream_sse_by_model
from app.session.stream.config import (
    HANDLER_ADVERSARIAL_HARNESS,
    HANDLER_OPENAI_DIRECT,
    resolve_adversarial_max_rounds_from_user_model,
    resolve_stream_handler_and_options,
)
from app.session.stream.context_factory import build_chat_stream_run_context
from app.session.stream.openai_direct import iter_chat_stream_sse_openai_direct
from app.session.stream.sse_format import sse_chunk, thinking_delta_from_piece

# 兼容旧路径 app.session.chat_stream_pipeline
iter_chat_stream_sse = iter_chat_stream_sse_openai_direct

__all__ = [
    "HANDLER_OPENAI_DIRECT",
    "HANDLER_ADVERSARIAL_HARNESS",
    "build_chat_stream_run_context",
    "iter_chat_stream_sse",
    "iter_chat_stream_sse_by_model",
    "iter_chat_stream_sse_openai_direct",
    "iter_chat_stream_sse_adversarial",
    "resolve_adversarial_max_rounds_from_user_model",
    "resolve_stream_handler_and_options",
    "sse_chunk",
    "thinking_delta_from_piece",
]
