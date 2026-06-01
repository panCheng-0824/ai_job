"""
ROLE005 chat 模式 — 从会话 history 提取最近若干轮问答，供面试官 Prompt 使用。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.session.user_turn_context import (
    assistant_turn_content_for_memory,
    user_turn_content_for_memory,
)

# chat 模式默认带入的问答轮次（一对 user/assistant 计为一轮）
DEFAULT_CHAT_QA_ROUNDS = 3


def extract_recent_qa_rounds(
    history_turns: List[Dict[str, Any]] | None,
    *,
    max_rounds: int = DEFAULT_CHAT_QA_ROUNDS,
) -> List[Tuple[str, str]]:
    """
    将 history 拆成 (学生, 面试官) 对，返回最近 ``max_rounds`` 对。

    不含本轮尚未 append 的当前输入（由调用方单独传入 ``question``）。
    """
    rounds: List[Tuple[str, str]] = []
    pending_user = ""
    for turn in history_turns or []:
        role = str(turn.get("role") or "").strip()
        if role == "user":
            if pending_user:
                rounds.append((pending_user, ""))
            pending_user = user_turn_content_for_memory(turn)
        elif role == "assistant":
            ans = assistant_turn_content_for_memory(turn)
            rounds.append((pending_user or "（无）", ans))
            pending_user = ""
    if pending_user:
        rounds.append((pending_user, ""))
    if max_rounds <= 0:
        return rounds
    return rounds[-max_rounds:]


def format_recent_qa_rounds_block(
    history_turns: List[Dict[str, Any]] | None,
    *,
    max_rounds: int = DEFAULT_CHAT_QA_ROUNDS,
) -> str:
    """格式化为 Prompt 中的「最近 N 轮面试对话」文本块。"""
    pairs = extract_recent_qa_rounds(history_turns, max_rounds=max_rounds)
    if not pairs:
        return "（尚无历史问答，本轮可视为会话开场。）"
    lines = [f"【最近面试对话（最多 {max_rounds} 轮）】"]
    for i, (user_text, asst_text) in enumerate(pairs, 1):
        lines.append(f"--- 第 {i} 轮 ---")
        lines.append(f"学生：{user_text or '（无）'}")
        lines.append(f"面试官：{asst_text or '（尚未回复）'}")
    return "\n".join(lines)
