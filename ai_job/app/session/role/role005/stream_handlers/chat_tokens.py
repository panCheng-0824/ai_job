"""
ROLE005 — SSE：chat 模式（综合最近三轮对话 + 当前问题，面试官 LLM 回复）。
"""

from __future__ import annotations

from threading import Event
from typing import Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role005.agents.chat_interviewer import run_chat_interviewer_agent
from app.session.role.role005.parsing import interviewer_display_text
from app.session.role.role005.stream_handlers.chat_guide import iter_chat_guide_tokens
from app.session.role.role005.stream_handlers.chat_history import (
    DEFAULT_CHAT_QA_ROUNDS,
    format_recent_qa_rounds_block,
)
from app.session.role.role_util.bindings import GraphBindings, is_cancelled
from app.session.role.role_util.stream_common import chunk_text


def iter_chat_tokens(
    bindings: GraphBindings,
    *,
    ctx: ChatStreamRunContext,
    question: str,
    materials_block: str,
    role_label: str,
    cancel_event: Event,
) -> Iterator[Dict[str, str]]:
    """
    聊天模式：不调答题图，由面试官 Agent 结合最近三轮 Q&A 与本轮输入生成下一问/追问。

    无有效输入且无历史时，降级为静态引导 JSON（与旧 chat_guide 一致）。
    """
    q = (question or "").strip()
    recent_block = format_recent_qa_rounds_block(
        ctx.history_turns,
        max_rounds=DEFAULT_CHAT_QA_ROUNDS,
    )

    yield {
        "type": "thinking",
        "content": (
            f"【{role_label}·聊天】正在结合最近 {DEFAULT_CHAT_QA_ROUNDS} 轮对话"
            f"与本轮输入生成面试官回复…\n"
        ),
    }

    if is_cancelled(bindings):
        return

    if not q and not (ctx.history_turns or []):
        yield from iter_chat_guide_tokens(cancel_event=cancel_event)
        return

    data, err = run_chat_interviewer_agent(
        bindings,
        recent_rounds_block=recent_block,
        materials_block=materials_block,
        current_question=q,
    )
    if err:
        yield {
            "type": "answer",
            "content": f"模拟面试官生成失败：{err}",
        }
        return

    display = interviewer_display_text(data)
    for piece in chunk_text(display):
        if cancel_event.is_set():
            break
        yield {"type": "answer", "content": piece}
