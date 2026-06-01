"""
ROLE005 — LLM JSON 输出解析与面试官动作校验。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple

from app.session.role.role_util.parsing import strip_markdown_json_fence


def parse_json_object(text: str) -> Tuple[Dict[str, Any], str]:
    """
    解析模型返回的 JSON 对象。

    返回 (data, error_message)；error 非空表示失败。
    """
    raw = strip_markdown_json_fence(text)
    if not raw:
        return {}, "模型输出为空"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, f"JSON 解析失败: {exc}"
    if not isinstance(data, dict):
        return {}, "根节点必须是 JSON 对象"
    return data, ""


def normalize_interviewer_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    规范化面试官输出字段，补默认 action。

    Interviewer 只允许提问类动作，不得包含评分字段。
    """
    action = str(data.get("action") or "ask_question").strip()
    allowed = {
        "ask_question",
        "ask_followup",
        "provide_hint",
        "clarify",
        "acknowledge",
    }
    if action not in allowed:
        action = "ask_question"
    out = dict(data)
    out["action"] = action
    # 剥离误输出的评分（红线：面试官不评价）
    for key in ("score", "total_score", "evaluation", "comment"):
        out.pop(key, None)
    return out


def interviewer_display_text(data: Dict[str, Any]) -> str:
    """将面试官 JSON 转为 SSE 展示用纯文本（仍保留 JSON 块供前端解析）。"""
    action = data.get("action", "")
    if action == "ask_followup":
        text = str(data.get("followup_text") or data.get("question_text") or "").strip()
    elif action == "provide_hint":
        text = str(data.get("thinking_hint") or data.get("hint_text") or "").strip()
    elif action == "clarify":
        text = str(data.get("clarify_text") or data.get("question_text") or "").strip()
    else:
        text = str(data.get("question_text") or "").strip()
    if not text:
        return json.dumps(data, ensure_ascii=False, indent=2)
    hint = str(data.get("thinking_hint") or "").strip()
    if hint and action in ("ask_question", "ask_followup"):
        return f"{text}\n\n（提示：{hint}）"
    return text
