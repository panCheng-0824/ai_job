"""
角色流水线 — SSE 流式入口共用辅助（用户模型合并、历史摘录、问题载体）。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterator, List, TypedDict

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.recent_dialog_excerpt import format_recent_dialog_excerpt
from app.session.user_turn_context import (
    assistant_turn_content_for_memory,
    user_turn_content_for_memory,
)
from user_model import MemoryTurn, UserModel, load_user_model


class ChatTokenStreamContext(TypedDict):
    """与 ``app.session.chat_service.stream_chat_service_tokens`` 一致的返回形状。"""

    usercode: str
    model_level: str
    token_iter: Iterator[Dict[str, str]]
    cancel: Callable[[], None]


def chunk_text(text: str, size: int = 48) -> Iterator[str]:
    """将长正文切成固定长度片段，模拟流式输出。"""
    content = text or ""
    for i in range(0, len(content), size):
        yield content[i : i + size]


def merge_stream_user(ctx: ChatStreamRunContext) -> UserModel:
    """合并磁盘用户模型与请求上下文中的 ``user_model``。"""
    disk = load_user_model(usercode=ctx.usercode)
    return {**dict(disk), **ctx.user_model}


def prepare_question_and_history(
    ctx: ChatStreamRunContext,
    *,
    merged_user: UserModel,
) -> tuple[str, str]:
    """准备「当前用户句」与「历史上下文字符串」。"""
    _ = merged_user
    question = (ctx.text or "").strip()
    memory: List[MemoryTurn] = []
    for turn in ctx.history_turns:
        role = turn.get("role")
        if role == "user":
            memory.append({"role": role, "content": user_turn_content_for_memory(turn)})
        elif role == "assistant":
            memory.append({"role": role, "content": assistant_turn_content_for_memory(turn)})

    history_block = ""
    if ctx.use_role_pipeline and memory:
        history_block = format_recent_dialog_excerpt(memory)

    return question, history_block


def build_full_question(
    *,
    role_sys: str,
    history_block: str,
    question: str,
    materials_block: str = "",
) -> str:
    """
    拼装传入 LangGraph 的「问题载体」。

    ``materials_block`` 可选：简历素材篮、OCR、岗位/企业卡片等（ROLE004 等使用）。
    """
    parts = [role_sys.strip()]
    if history_block.strip():
        parts.append(history_block.strip())
    if materials_block.strip():
        parts.append(materials_block.strip())
    parts.append(f"用户本轮问题：\n{question}")
    return "\n\n".join(p for p in parts if p).strip()


def role_display_name(merged_user: UserModel, *, fallback: str = "AI 助手") -> str:
    """从用户模型取角色展示名，用于 thinking 阶段文案。"""
    profile = merged_user.get("user_profile")
    if isinstance(profile, dict):
        name = str(profile.get("role_name", "")).strip()
        if name:
            return name
    return fallback
