"""
ROLE005 — 上下文卡片单条解析（与 ROLE004 素材格式复用截断策略）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.session.role.role004.materials import _format_job_body, truncate_text

# 单条素材、岗位描述、整篮素材的上限（与 ROLE004 环境变量体系一致）
_MAX_CARD_BODY = 3500
_MAX_COMPANY_DESC = 2000


def kind_label(kind: str) -> str:
    """将卡片 kind 转为中文展示标签。"""
    mapping = {
        "resume_draft": "左侧当前简历草稿",
        "ocr": "简历",
        "resume": "简历",
        "job": "岗位",
        "company": "企业",
        "interview_session": "面试会话",
    }
    return mapping.get(kind, "素材")


def format_card_body(card: Dict[str, Any]) -> str:
    """
    解析单张上下文卡片的可读正文。

    支持 payload 嵌套或扁平结构；面试会话卡原样 JSON 便于调试。
    """
    kind = str(card.get("kind") or card.get("type") or "").strip()
    payload = card.get("payload") if isinstance(card.get("payload"), dict) else card
    if not isinstance(payload, dict):
        return truncate_text(str(card.get("text") or card.get("content") or ""), _MAX_CARD_BODY)

    if kind == "job":
        return _format_job_body(payload)
    if kind in ("resume", "ocr", "resume_draft"):
        text = (
            payload.get("text")
            or payload.get("content")
            or payload.get("raw_text")
            or ""
        )
        return truncate_text(str(text).strip(), _MAX_CARD_BODY)
    if kind == "company":
        name = payload.get("company_name") or payload.get("name") or ""
        desc = payload.get("description") or payload.get("intro") or ""
        parts: List[str] = [f"企业：{name}"] if name else []
        if desc:
            parts.append(truncate_text(str(desc).strip(), _MAX_COMPANY_DESC))
        return "\n".join(parts).strip()
    if kind == "interview_session":
        # 业务卡：含 interview_session_id，供联调识别
        return json.dumps(payload, ensure_ascii=False)
    return truncate_text(json.dumps(payload, ensure_ascii=False), _MAX_CARD_BODY)
