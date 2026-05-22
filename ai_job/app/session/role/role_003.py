from __future__ import annotations

from threading import Event
from typing import Any, Callable, Dict, Iterator, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from openai import OpenAI
from openai import NotFoundError as OpenAINotFoundError

from app.session.chat_service import stream_chat_service_tokens as base_stream_chat_service_tokens
from app.session.chat_stream_context import ChatStreamRunContext
from model_cfg import load_model_list
from lc_agent.selection import select_model_by_level
from role_pipeline import compress_context_to_messages, denoise_question
from user_model import build_system_prompt_from_user, load_role_profiles, load_user_model
from user_session import run_user_query_for_runtime_session


class ChatServiceResult(TypedDict):
    """HTTP/控制器层使用的统一返回结构。"""

    answer: str
    raw_result: Dict[str, Any]


class ChatTokenStreamContext(TypedDict):
    """SSE 流式输出所需的上下文结构。"""

    usercode: str
    model_level: str
    token_iter: Iterator[Dict[str, str]]
    cancel: Callable[[], None]


def stream_chat_service_tokens(ctx: ChatStreamRunContext) -> ChatTokenStreamContext:
    """默认与全局直连流一致；此角色如需定制，在本函数内改写组装或迭代逻辑。"""
    return base_stream_chat_service_tokens(
        usercode=ctx.usercode,
        message=ctx.text,
        history=ctx.history_turns,
        temperature=ctx.temperature,
        use_role_pipeline=ctx.use_role_pipeline,
        system_prompt_extra=ctx.system_prompt_extra or None,
    )