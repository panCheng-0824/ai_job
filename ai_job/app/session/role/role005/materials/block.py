"""
ROLE005 — 多卡片合并为 Planner 素材块与素材指纹。
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from app.session.role.role004.materials import truncate_text
from app.session.role.role005.materials.cards import format_card_body, kind_label

_MAX_MATERIALS_CHARS = 12000


def build_interview_materials_block(
    *,
    message_context: str = "",
    context_cards: List[Dict[str, Any]] | None = None,
) -> str:
    """
    将简历/岗位/企业等卡片拼成 Planner 可用的素材块。

    顺序：附加上下文（message_context）→ 各卡片（带中文标签）。
    """
    lines: List[str] = []
    hidden = (message_context or "").strip()
    if hidden:
        lines.append("【附加上下文】")
        lines.append(truncate_text(hidden, 4000))

    for i, card in enumerate(context_cards or []):
        if not isinstance(card, dict):
            continue
        kind = str(card.get("kind") or card.get("type") or "material").strip()
        body = format_card_body(card)
        if not body:
            continue
        lines.append("")
        lines.append(f"【{kind_label(kind)}·素材{i + 1}】")
        lines.append(body)

    block = "\n".join(lines).strip()
    return truncate_text(block, _MAX_MATERIALS_CHARS)


def compute_material_hash(materials_block: str) -> str:
    """素材 SHA256 指纹（前 32 位），用于大纲缓存键与 server_job 溯源。"""
    raw = (materials_block or "").strip().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


_JOB_CARD_KIND = "job"
_DEFAULT_TARGET_ROLE = "技术岗位"


def _card_kind(card: Dict[str, Any]) -> str:
    return str(card.get("kind") or card.get("type") or "").strip()


def _card_payload(card: Dict[str, Any]) -> Dict[str, Any]:
    payload = card.get("payload")
    if isinstance(payload, dict):
        return payload
    return card


def _title_from_job_card(card: Dict[str, Any]) -> str:
    """从岗位卡片 payload 取职位名（与 ROLE004 format_job_body 字段对齐）。"""
    payload = _card_payload(card)
    title = (
        payload.get("job_title")
        or payload.get("job_name")
        or payload.get("title")
        or ""
    )
    return str(title).strip()


def _title_from_materials_block(materials_block: str) -> str:
    """从拼好的素材正文里解析 ``岗位名称：`` 行（format_job_body 会写入）。"""
    for line in (materials_block or "").splitlines():
        if line.startswith("岗位名称："):
            return line.replace("岗位名称：", "", 1).strip()
    return ""


def extract_target_role(
    materials_block: str = "",
    *,
    context_cards: List[Dict[str, Any]] | None = None,
) -> str:
    """
    提取「目标岗位」字符串，供 Planner 提示词与大纲语义缓存使用。

    优先级
    ------
    1. ``context_cards`` 中第一张 ``job`` 卡的 ``job_title`` / ``job_name``；
    2. ``materials_block`` 文本中的 ``岗位名称：`` 行；
    3. 默认 ``技术岗位``。
    """
    for card in context_cards or []:
        if not isinstance(card, dict):
            continue
        if _card_kind(card) != _JOB_CARD_KIND:
            continue
        title = _title_from_job_card(card)
        if title:
            return title

    from_text = _title_from_materials_block(materials_block)
    if from_text:
        return from_text
    return _DEFAULT_TARGET_ROLE
