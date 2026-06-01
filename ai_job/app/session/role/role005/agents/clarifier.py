"""
ROLE005 — 题目澄清 Agent（学生提出疑问时）。
"""

from __future__ import annotations

from app.session.role.role005.agents._llm import invoke_llm_text
from app.session.role.role005.domain.models import ContextBundle
from app.session.role.role_util.bindings import GraphBindings


def run_clarifier_agent(
    bindings: GraphBindings,
    *,
    bundle: ContextBundle,
    student_text: str,
) -> str:
    """返回澄清说明文本（自然语言，由 interviewer 包装为 JSON）。"""
    session = bundle.session
    plan = bundle.plan
    q_idx = session.current_question_index
    current = plan.questions[q_idx] if q_idx < len(plan.questions) else None
    q_text = current.text if current else ""

    prompt = f"""你是面试题澄清助手。学生对本题有疑问，请用简短中文解释题意与作答范围。
**禁止**给出答案或解题步骤。

题目：{q_text}
学生疑问：{student_text}
"""
    return invoke_llm_text(bindings, prompt) or "请围绕题目考察的能力点作答，可结合你真实项目经历说明。"
