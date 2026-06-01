"""ROLE004 — 素材块合并与生成节点上下文。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.session.role.role004.materials.cards import format_context_cards_block
from app.session.role.role004.materials.truncate import (
    MAX_MATERIALS_BLOCK_CHARS,
    MAX_STUDENT_CONTEXT_CHARS,
    truncate_text,
)


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
