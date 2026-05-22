"""
ROLE004 — 结构化简历 JSON 解析与规整（对齐前端 parseResumeContent + 6 种模版）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from app.session.role.role004.resume_templates import (
    DEFAULT_TEMPLATE_ID,
    build_basic_skeleton,
    build_intent_skeleton,
    get_template,
    map_section_key_to_template,
)
from app.session.role.role_util.parsing import strip_markdown_json_fence


def _normalize_section_items(raw: Any) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                title = str(entry.get("title") or "").strip()
                body = str(entry.get("body") or entry.get("content") or "").strip()
                if title or body:
                    items.append({"title": title, "body": body})
            elif entry is not None:
                body = str(entry).strip()
                if body:
                    items.append({"title": "", "body": body})
    elif isinstance(raw, str) and raw.strip():
        items.append({"title": "", "body": raw.strip()})
    return items


def normalize_resume_content(
    data: Dict[str, Any],
    *,
    template_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    将模型输出规整为前端可 ``parseResumeContent`` 的结构。

    返回字段含 ``templateId``，供前端校验或与左侧 ``selectedTemplateId`` 对照。
    """
    tid = str(
        data.get("templateId")
        or data.get("template_id")
        or template_id
        or DEFAULT_TEMPLATE_ID
    ).strip()
    tpl = get_template(tid)

    basic_raw = data.get("basic") if isinstance(data.get("basic"), dict) else {}
    basic = build_basic_skeleton()
    for key in basic:
        if key in basic_raw:
            basic[key] = str(basic_raw.get(key) or "").strip()

    intent_raw = data.get("intent") if isinstance(data.get("intent"), dict) else {}
    intent = build_intent_skeleton(tpl)
    intent["targetJobs"] = str(
        intent_raw.get("targetJobs") or intent_raw.get("target_jobs") or ""
    ).strip()
    intent["targetCompanies"] = str(
        intent_raw.get("targetCompanies") or intent_raw.get("target_companies") or ""
    ).strip()

    sections_raw = data.get("sections") if isinstance(data.get("sections"), dict) else {}
    sections: Dict[str, List[Dict[str, str]]] = tpl.empty_sections_skeleton()

    for raw_key, raw_val in sections_raw.items():
        mapped = map_section_key_to_template(str(raw_key), tpl)
        if not mapped:
            continue
        items = _normalize_section_items(raw_val)
        if items:
            sections[mapped] = items

    return {
        "templateId": tpl.id,
        "basic": basic,
        "intent": intent,
        "sections": sections,
        "extraNotes": str(data.get("extraNotes") or data.get("extra_notes") or "").strip(),
    }


def parse_resume_content_blob(
    text: str,
    *,
    template_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    解析生成通道的 JSON。

    返回 (resume_content, parse_error)；error 非空表示使用了降级空壳。
    """
    raw = strip_markdown_json_fence(text)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return normalize_resume_content(data, template_id=template_id), ""
    except json.JSONDecodeError:
        pass
    fallback = normalize_resume_content({"templateId": template_id or DEFAULT_TEMPLATE_ID})
    return fallback, "模型输出不是合法 JSON，已返回空简历骨架，请重试或补充素材。"
