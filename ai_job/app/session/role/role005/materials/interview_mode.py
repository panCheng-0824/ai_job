"""
ROLE005 — 遮层面试模式 message_context 解析与 Redis key 构造。

web 经隐藏 ``message_context`` 传入 JSON，含 ``mode=interview``、``action``、``ctx_key`` 等字段。
"""

from __future__ import annotations

import json
from typing import Any, Dict


def parse_interview_mode_context(message_context: str) -> Dict[str, Any]:
    """
    解析遮层面试模式的隐藏上下文。

    期望 JSON::

        {
          "mode": "interview",
          "action": "start|answer",
          "student_id": "...",
          "record_id": "...",
          "interview_session_id": "...",
          "chat_session_id": "...",
          "ctx_key": "interview:ctx:...",
          "question_session_key": "interview:qsess:...",
          "question_id": "...",
          "seq_no": 0
        }
    """
    raw = (message_context or "").strip()
    if not raw.startswith("{"):
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    if str(data.get("mode") or "").strip() != "interview":
        return {}
    return data


def is_interview_mode_context(message_context: str) -> bool:
    """message_context 是否为遮层面试模式。"""
    return bool(parse_interview_mode_context(message_context))


def build_question_session_key(
    chat_session_id: str,
    student_id: str,
    record_id: str,
    question_id: str,
) -> str:
    """与 server_job ``InterviewRedisKeys.questionSession`` 对齐。"""
    cs = (chat_session_id or "").strip()
    sid = (student_id or "").strip()
    rid = (record_id or "").strip()
    qid = (question_id or "").strip()
    return f"interview:qsess:{cs}:{sid}:{rid}:{qid}"


def merge_turn_ctx_from_mode(mode_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    将遮层模式上下文转为答题图可用的 turn_ctx。

    保留 ``mode=interview`` 供后续 MQ 分支识别。
    """
    action = str(mode_ctx.get("action") or "answer").strip()
    out: Dict[str, Any] = {
        "mode": "interview",
        "action": action,
        "interview_session_id": str(mode_ctx.get("interview_session_id") or "").strip(),
        "record_id": str(mode_ctx.get("record_id") or "").strip(),
        "student_id": str(mode_ctx.get("student_id") or "").strip(),
        "chat_session_id": str(mode_ctx.get("chat_session_id") or "").strip(),
        "ctx_key": str(mode_ctx.get("ctx_key") or "").strip(),
        "question_id": str(mode_ctx.get("question_id") or "").strip(),
    }
    if mode_ctx.get("seq_no") is not None:
        try:
            out["seq_no"] = int(mode_ctx.get("seq_no"))
        except (TypeError, ValueError):
            pass
    qs_key = str(mode_ctx.get("question_session_key") or "").strip()
    if qs_key:
        out["question_session_key"] = qs_key
    payload = mode_ctx.get("payload")
    if isinstance(payload, dict):
        out["payload"] = payload
    return out
