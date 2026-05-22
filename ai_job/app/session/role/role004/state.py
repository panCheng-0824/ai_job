"""
ROLE004 LangGraph 状态定义 — 简历优化师。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from app.session.role.role004.intent import Role004Intent


@dataclass
class ResumeOptimizeState:
    """
    简历优化师图内状态。

    intent:
        ``resume_advise`` — 段落/表述优化建议（原文 vs 改后）；
        ``resume_generate`` — 综合素材生成可渲染的结构化简历。
    materials_block:
        由 OCR、岗位/企业卡片、附加上下文等拼成的素材摘录。
    resume_content:
        生成通道产出的简历 JSON（与前端 ``parseResumeContent`` 同构，含 ``templateId``）。
    template_id:
        目标简历模版 id（与 ``resume_templates.RESUME_TEMPLATES`` 一致，如 ``standard_cn``）。
    """

    question: str = ""
    user_query: str = ""
    student_context: str = ""
    materials_block: str = ""
    template_id: str = "standard_cn"
    intent: Role004Intent = "resume_advise"
    final_answer: str = ""
    resume_content: Dict[str, Any] = field(default_factory=dict)
