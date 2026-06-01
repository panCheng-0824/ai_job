"""
ROLE004 — 简历素材篮与附加上下文（分层：截断 / 卡片 / 合并块）。
"""

from app.session.role.role004.materials.block import (
    build_generate_context_block,
    build_materials_block,
    materials_substantial,
)
from app.session.role.role004.materials.cards import format_context_cards_block, format_job_body

# 兼容 ROLE005 等对私有名的引用
_format_job_body = format_job_body
from app.session.role.role004.materials.truncate import truncate_text

__all__ = [
    "truncate_text",
    "format_context_cards_block",
    "format_job_body",
    "_format_job_body",
    "build_materials_block",
    "materials_substantial",
    "build_generate_context_block",
]
