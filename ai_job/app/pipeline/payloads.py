"""角色管道各阶段的文本载荷构造工具。

这些辅助函数用于在不同管道步骤中保持输入格式一致。
"""

from __future__ import annotations

import json
from typing import List, Optional

from user_model import MemoryTurn, UserModel


def memory_turns_to_plain(memory: List[MemoryTurn]) -> str:
    """把结构化历史轮次转换为紧凑的角色标注纯文本。"""
    lines: List[str] = []
    for turn in memory:
        who = "用户" if turn["role"] == "user" else "助手"
        lines.append(f"[{who}] {turn['content'].strip()}")
    return "\n".join(lines)


def build_adversarial_payload(denoised_question: str, agent_answer: str) -> str:
    """构造对抗审查阶段的输入载荷。"""
    normalized_answer = (agent_answer or "").strip() or "（空）"
    return (
        "【净化后的核心问题】\n"
        f"{(denoised_question or '').strip()}\n\n"
        "【主模型回答】\n"
        f"{normalized_answer}\n"
    )


def build_profile_enrichment_payload(
    user: UserModel,
    *,
    denoised_question: str,
    agent_answer: str,
    context_summary: Optional[str],
    adversarial_review_text: Optional[str] = None,
) -> str:
    """基于当前上下文与回答构造画像补充阶段输入。"""
    profile_json = json.dumps(user["user_profile"], ensure_ascii=False, indent=2)
    goals_txt = "\n".join(f"- {g}" for g in user["goals"]) if user["goals"] else "（无）"
    hist = (context_summary or "").strip() or "（无历史摘要：本轮无前文压缩内容或记忆为空）"
    adv = (adversarial_review_text or "").strip()

    payload_parts = [
        "【当前 user_profile】\n" + profile_json,
        "【当前 goals】\n" + goals_txt,
        "【历史上下文摘要（来自压缩管道，概括多轮前情）】\n" + hist,
        "【本轮净化后的用户问题】\n" + (denoised_question or "").strip(),
        "【本轮主助手回答】\n" + ((agent_answer or "").strip() or "（空）"),
    ]
    if adv:
        payload_parts.append("【可选：本轮对抗审查摘要】\n" + adv)
    return "\n\n".join(payload_parts)
