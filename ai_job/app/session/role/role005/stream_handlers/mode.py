"""
ROLE005 — 判定本轮 SSE 应走的业务模式。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.session.role.role005.materials.turn_context import (
    context_cards_include_resume_and_job,
)

# 用户自然语言触发规划预览的关键词
_PLAN_PREVIEW_KEYWORDS = (
    "面试规划",
    "准备好了",
    "面试大纲",
    "做好面试准备",
    "面试题目",
)


def detect_stream_mode(
    user_display_content: str,
    user_context_cards: List[Dict[str, Any]] | None,
    turn_ctx: Dict[str, Any],
) -> str:
    """
    判定本轮 SSE 模式。

    返回
    ----
    ``turn`` :
        message_context 含 ``interview_session_id`` 与 ``action``，走答题图。
    ``plan_preview`` :
        用户消息含规划类关键词，且 ``user_context_cards`` 中同时含简历与岗位卡片。
    ``chat`` :
        综合最近三轮对话与本轮输入，走面试官 LLM（``iter_chat_tokens``）。
    """
    if turn_ctx.get("mode") == "interview":
        action = str(turn_ctx.get("action") or "answer").strip()
        if action == "start":
            return "interview_start"
        return "interview_turn"
    if turn_ctx.get("interview_session_id") and turn_ctx.get("action"):
        return "turn"
    q = (user_display_content or "").lower()
    keyword_hit = any(k in q for k in _PLAN_PREVIEW_KEYWORDS)
    if keyword_hit and context_cards_include_resume_and_job(user_context_cards):
        return "plan_preview"
    return "chat"
