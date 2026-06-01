"""
ROLE005 — 面试素材提取（简历 / 岗位 / 企业上下文卡片）。

按职责拆分：
- ``cards``：单卡片正文格式化
- ``block``：拼成 Planner 素材块与指纹
- ``turn_context``：从 message_context 解析 turn 指令
"""

from app.session.role.role005.materials.block import (
    build_interview_materials_block,
    compute_material_hash,
    extract_target_role,
)
from app.session.role.role005.materials.turn_context import (
    build_snapshots_from_cards,
    context_cards_include_resume_and_job,
    parse_interview_turn_from_context,
)

__all__ = [
    "build_interview_materials_block",
    "compute_material_hash",
    "extract_target_role",
    "parse_interview_turn_from_context",
    "build_snapshots_from_cards",
    "context_cards_include_resume_and_job",
]
