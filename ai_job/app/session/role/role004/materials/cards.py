"""ROLE004 — context_cards 格式化。"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.session.role.role004.materials.truncate import (
    MAX_CARD_BODY_CHARS,
    MAX_JOB_DESC_CHARS,
    truncate_text,
)


def _kind_label(kind: str) -> str:
    if kind == "resume_draft":
        return "左侧当前简历草稿"
    if kind == "ocr" or kind == "resume":
        return "简历"
    if kind == "job":
        return "岗位"
    if kind == "company":
        return "企业"
    return "素材"


def format_job_body(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    lines: List[str] = []
    title = payload.get("job_title") or payload.get("job_name") or payload.get("job_id")
    if title:
        lines.append(f"岗位名称：{title}")
    city = payload.get("city") or payload.get("district")
    if city:
        lines.append(f"工作地点：{city}")
    rel = payload.get("company_relation") if isinstance(payload.get("company_relation"), dict) else {}
    company = payload.get("company_name") or rel.get("company_name")
    if company:
        lines.append(f"招聘企业：{company}")
    salary = payload.get("salary") or payload.get("salary_range")
    if salary:
        lines.append(f"薪资：{salary}")
    if payload.get("education"):
        lines.append(f"学历：{payload['education']}")
    desc = (
        payload.get("job_desc")
        or payload.get("job_description")
        or payload.get("description")
        or payload.get("requirement")
        or payload.get("job_requirement")
    )
    if desc:
        lines.append("")
        lines.append(truncate_text(str(desc).strip(), MAX_JOB_DESC_CHARS))
    return "\n".join(lines).strip()


def _format_company_body(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    lines: List[str] = []
    if payload.get("company_name"):
        lines.append(f"企业名称：{payload['company_name']}")
    if payload.get("industry"):
        lines.append(f"行业：{payload['industry']}")
    if payload.get("credit_code"):
        lines.append(f"统一社会信用代码：{payload['credit_code']}")
    intro = payload.get("intro") or payload.get("description") or payload.get("company_intro")
    if intro:
        lines.append("")
        lines.append(truncate_text(str(intro).strip(), MAX_JOB_DESC_CHARS))
    return "\n".join(lines).strip()


def _card_body(card: Dict[str, Any]) -> str:
    kind = str(card.get("type") or card.get("kind") or "").strip().lower()
    payload = card.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"text": payload}
    if not isinstance(payload, dict):
        payload = {}

    if kind == "resume_draft":
        text = str(payload.get("preview_text") or payload.get("text") or "").strip()
        return truncate_text(text, MAX_CARD_BODY_CHARS)
    if kind in ("ocr", "resume"):
        return truncate_text(
            str(payload.get("text") or payload.get("content") or "").strip(),
            MAX_CARD_BODY_CHARS,
        )
    if kind == "job":
        return format_job_body(payload)
    if kind == "company":
        return _format_company_body(payload)
    ctx = str(card.get("message_context") or "").strip()
    if ctx:
        return ctx
    return str(payload.get("text") or "").strip()


def format_context_cards_block(cards: List[Dict[str, Any]]) -> str:
    """将 ``context_cards`` 转为模型可读的素材摘录块。"""
    if not cards:
        return ""
    blocks: List[str] = []
    ordered = sorted(
        [c for c in cards if isinstance(c, dict)],
        key=lambda c: (
            0
            if str(c.get("type") or c.get("kind") or "").strip().lower() == "resume_draft"
            else 1
        ),
    )
    for card in ordered:
        kind = str(card.get("type") or card.get("kind") or "material").strip()
        title = str(card.get("title") or card.get("ref_id") or "").strip()
        subtitle = str(card.get("subtitle") or "").strip()
        head = f"【{_kind_label(kind)}】{title}"
        if subtitle:
            head += f" · {subtitle}"
        body = _card_body(card)
        blocks.append(f"{head}\n{body}" if body else head)
    if not blocks:
        return ""
    header = f"【简历优化素材篮】共 {len(blocks)} 项"
    return header + "\n\n" + "\n\n────────────────\n\n".join(blocks)
