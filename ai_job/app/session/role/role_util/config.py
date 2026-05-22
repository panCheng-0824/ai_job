"""
角色流水线 — 从 usermodel.json 抽取运行时配置（多角色共用）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from langchain_core.tools import BaseTool

from lc_agent.builtin_tools import build_builtin_tools_by_names


def format_common_mistakes(val: Any) -> str:
    """将 ``common_mistakes`` 统一为一行中文。"""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, list):
        return "；".join(str(x).strip() for x in val if str(x).strip())
    return ""


def tools_from_user_model(user_model: Dict[str, Any]) -> Tuple[List[BaseTool], Dict[str, BaseTool]]:
    """根据用户模型 ``tools`` 字段解析 LangChain 工具列表与 name 索引。"""
    raw = user_model.get("tools") or []
    names = [str(n).strip() for n in raw if str(n).strip()]
    tools = build_builtin_tools_by_names(names)
    return tools, {t.name: t for t in tools}


def build_role_block(user_row: Dict[str, Any]) -> str:
    """
    从用户模型记录抽取「规划 / 执行 / 收尾」共用的角色约束文本。

    与 ``build_system_prompt_from_user`` 字段同源，条目化排版便于各节点阅读。
    """
    profile = user_row.get("user_profile") if isinstance(user_row.get("user_profile"), dict) else {}
    lines: List[str] = []

    role_name = str(profile.get("role_name", "")).strip()
    domain = str(profile.get("domain", "")).strip()
    if role_name:
        lines.append(f"【角色】{role_name}" + (f"（领域：{domain}）" if domain else ""))
    elif domain:
        lines.append(f"【领域】{domain}")

    tone = str(profile.get("tone", "")).strip()
    if tone:
        lines.append(f"【语气】{tone}")

    caps = profile.get("core_capabilities")
    if isinstance(caps, list) and caps:
        joined = "、".join(str(c).strip() for c in caps if str(c).strip())
        if joined:
            lines.append(f"【核心能力（规划步骤应尽量覆盖）】{joined}")

    goals = user_row.get("goals") or []
    if isinstance(goals, list) and goals:
        goal_line = [str(g).strip() for g in goals if str(g).strip()]
        if goal_line:
            lines.append("【角色目标】" + "；".join(goal_line))

    base_sys = str(user_row.get("sys_prompt", "")).strip()
    if base_sys:
        lines.append(f"【系统设定摘要】{base_sys}")

    user_prompt = str(user_row.get("user_prompt", "")).strip()
    if user_prompt:
        lines.append(f"【对话/回复偏好】{user_prompt}")

    output_format = str(user_row.get("output_format", "")).strip()
    if output_format:
        lines.append(f"【输出结构约束（最终答复必须对齐）】{output_format}")

    mistakes = format_common_mistakes(user_row.get("common_mistakes"))
    if mistakes:
        lines.append(f"【须规避的回复模式】{mistakes}")

    forbidden = user_row.get("forbidden_topics")
    if isinstance(forbidden, list) and forbidden:
        topics = "、".join(str(t).strip() for t in forbidden if str(t).strip())
        if topics:
            lines.append(f"【禁止话题】{topics}")

    risk = str(user_row.get("risk_reminder", "")).strip()
    if risk:
        lines.append(f"【风险提醒】{risk}")

    clarify = str(user_row.get("clarification_question", "")).strip()
    if clarify:
        lines.append(f"【信息不足时可参考的追问】{clarify}")

    greeting = str(user_row.get("greeting_example", "")).strip()
    closing = str(user_row.get("conversation_exit", "")).strip()
    interaction: List[str] = []
    if greeting:
        interaction.append(f"开场参考：{greeting}")
    if closing:
        interaction.append(f"收尾参考：{closing}")
    if interaction:
        lines.append("【交互话术参考】" + " ".join(interaction))

    tool_names = user_row.get("tools") or []
    if isinstance(tool_names, list) and tool_names:
        names = "、".join(str(t).strip() for t in tool_names if str(t).strip())
        if names:
            lines.append(f"【配置的可调用工具名】{names}")

    return "\n".join(lines) if lines else "（未提供额外角色配置）"


def build_plan_execute_role_block(user_row: Dict[str, Any]) -> str:
    """ROLE001 兼容别名，与 ``build_role_block`` 相同。"""
    return build_role_block(user_row)


def resolve_use_structured_return(user: Dict[str, Any]) -> bool:
    """是否启用末尾 structured_return（JSON + summary）。"""
    opts = user.get("stream_options")
    if isinstance(opts, dict) and "use_structured_return" in opts:
        return bool(opts["use_structured_return"])
    if "use_structured_return" in user:
        return bool(user["use_structured_return"])
    return False
