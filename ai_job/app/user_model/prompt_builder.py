"""主对话 Agent 的提示词拼装辅助。"""

from __future__ import annotations

import json
from typing import List

from .types import UserModel


def build_system_prompt_from_user(user: UserModel) -> str:
    """根据角色画像、目标和风格偏好拼装 system prompt。"""
    blocks: List[str] = []

    blocks.append(
        "【角色标识】\n"
        f"- username（角色标识名）: {user['username']}\n"
        f"- usercode（角色稳定编号）: {user['usercode']}"
    )

    base = user["sys_prompt"].strip()
    if base:
        blocks.append(base)

    lines_profile: List[str] = []
    for key, value in user["user_profile"].items():
        if isinstance(value, (dict, list)):
            value_txt = json.dumps(value, ensure_ascii=False)
        else:
            value_txt = str(value)
        lines_profile.append(f"- {key}: {value_txt}")
    if lines_profile:
        blocks.append("【角色画像】\n" + "\n".join(lines_profile))

    goals = [g.strip() for g in user["goals"] if g.strip()]
    if goals:
        blocks.append("【角色目标】\n" + "\n".join(f"- {g}" for g in goals))

    user_style = user["user_prompt"].strip()
    if user_style:
        blocks.append("【对话偏好 / 角色侧补充说明】\n" + user_style)

    tools = [str(t).strip() for t in user.get("tools", []) if str(t).strip()]
    if tools:
        blocks.append("【可调用工具】\n" + "\n".join(f"- {name}" for name in tools))

    output_format = str(user.get("output_format", "")).strip()
    if output_format:
        blocks.append("【输出结构约束】\n" + output_format)

    interaction_lines: List[str] = []
    greeting_example = str(user.get("greeting_example", "")).strip()
    if greeting_example:
        interaction_lines.append(f"- 开场白参考: {greeting_example}")
    clarification_question = str(user.get("clarification_question", "")).strip()
    if clarification_question:
        interaction_lines.append(f"- 信息不足时优先追问: {clarification_question}")
    conversation_exit = str(user.get("conversation_exit", "")).strip()
    if conversation_exit:
        interaction_lines.append(f"- 结束语参考: {conversation_exit}")
    if interaction_lines:
        blocks.append("【交互体验约束】\n" + "\n".join(interaction_lines))

    safety_lines: List[str] = []
    forbidden_topics = user.get("forbidden_topics", [])
    if isinstance(forbidden_topics, list):
        clean_topics = [str(topic).strip() for topic in forbidden_topics if str(topic).strip()]
        if clean_topics:
            safety_lines.append("- 禁止话题: " + "、".join(clean_topics))

    risk_reminder = str(user.get("risk_reminder", "")).strip()
    if risk_reminder:
        safety_lines.append("- 风险提醒模板: " + risk_reminder)

    common_mistakes = user.get("common_mistakes")
    if isinstance(common_mistakes, str) and common_mistakes.strip():
        safety_lines.append("- 常见错误规避: " + common_mistakes.strip())
    elif isinstance(common_mistakes, list):
        clean_mistakes = [str(item).strip() for item in common_mistakes if str(item).strip()]
        if clean_mistakes:
            safety_lines.append("- 常见错误规避: " + "；".join(clean_mistakes))

    if safety_lines:
        blocks.append("【安全与边界】\n" + "\n".join(safety_lines))

    return "\n\n".join(blocks)
