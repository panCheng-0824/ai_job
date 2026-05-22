"""
ROLE004 — 简历素材篮与附加上下文格式化。
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

_TRUNC_SUFFIX = "…（内容过长已截断，请结合已有信息生成）"

# 单条素材正文、岗位描述、整篮素材的上限（可通过环境变量覆盖）
def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(500, int(raw))
    except ValueError:
        return default


MAX_CARD_BODY_CHARS = _env_int("ROLE004_MAX_CARD_BODY_CHARS", 3500)
MAX_JOB_DESC_CHARS = _env_int("ROLE004_MAX_JOB_DESC_CHARS", 1800)
MAX_MATERIALS_BLOCK_CHARS = _env_int("ROLE004_MAX_MATERIALS_BLOCK_CHARS", 10000)
MAX_STUDENT_CONTEXT_CHARS = _env_int("ROLE004_MAX_STUDENT_CONTEXT_CHARS", 3500)


def truncate_text(text: str, max_chars: int, *, suffix: str = _TRUNC_SUFFIX) -> str:
    """截断过长文本，避免简历生成请求超时。"""
    raw = (text or "").strip()
    if max_chars <= 0 or len(raw) <= max_chars:
        return raw
    keep = max(200, max_chars - len(suffix))
    return raw[:keep] + suffix


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


def _format_job_body(payload: Dict[str, Any]) -> str:
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
        return _format_job_body(payload)
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


def build_materials_block(
    *,
    message_context: str = "",
    context_cards: List[Dict[str, Any]] | None = None,
) -> str:
    """合并隐藏附加上下文与上下文卡片为单一素材块。"""
    parts: List[str] = []
    cards_block = format_context_cards_block(list(context_cards or []))
    if cards_block:
        parts.append(cards_block)
    hidden = (message_context or "").strip()
    if hidden:
        parts.append(f"【用户附加上下文】\n{truncate_text(hidden, MAX_MATERIALS_BLOCK_CHARS)}")
    merged = "\n\n".join(parts).strip()
    return truncate_text(merged, MAX_MATERIALS_BLOCK_CHARS)


def materials_substantial(materials_block: str, *, min_chars: int = 120) -> bool:
    """素材是否足够支撑「生成整份简历」通道。"""
    return len((materials_block or "").strip()) >= min_chars


def build_generate_context_block(
    *,
    user_query: str = "",
    student_context: str = "",
    materials_block: str = "",
) -> str:
    """
    生成节点专用上下文（避免重复塞入完整 ``state.question`` 导致超长与超时）。
    """
    parts: List[str] = []
    materials_raw = (materials_block or "").strip()
    if "【左侧当前简历草稿】" in materials_raw or "左侧当前简历草稿" in materials_raw:
        parts.append(
            "【优化基准说明】以素材篮中「左侧当前简历草稿」为待优化正文；"
            "OCR/岗位/企业等参考素材仅用于补全、对齐意向与润色，勿脱离草稿凭空重写。"
        )
    query = (user_query or "").strip()
    if query:
        parts.append(f"【用户本轮诉求】\n{query}")
    profile = truncate_text((student_context or "").strip(), MAX_STUDENT_CONTEXT_CHARS)
    if profile:
        parts.append(f"【学生档案摘要】\n{profile}")
    materials = truncate_text((materials_block or "").strip(), MAX_MATERIALS_BLOCK_CHARS)
    if materials:
        parts.append(materials)
    return "\n\n".join(parts).strip() or "（无额外上下文）"
