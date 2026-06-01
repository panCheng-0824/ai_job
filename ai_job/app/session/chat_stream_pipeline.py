"""
会话 SSE 流 — 兼容入口，实现已迁移至 ``app.session.stream``。

业务语义
--------
- 每条 ``usermodel.json`` 条目定义 ``stream_handler`` / ``stream_options``
- 页面开关 ``use_adversarial_harness`` / ``use_role_pipeline`` 优先于配置
- 角色 LangGraph 流走 ``iter_chat_stream_sse_by_model``（按 usercode 注册表派发）
"""

from app.session.stream import (
    HANDLER_ADVERSARIAL_HARNESS,
    HANDLER_OPENAI_DIRECT,
    build_chat_stream_run_context,
    iter_chat_stream_sse,
    iter_chat_stream_sse_adversarial,
    iter_chat_stream_sse_by_model,
    iter_chat_stream_sse_openai_direct,
    resolve_adversarial_max_rounds_from_user_model,
    resolve_stream_handler_and_options,
    sse_chunk,
    thinking_delta_from_piece,
)

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
