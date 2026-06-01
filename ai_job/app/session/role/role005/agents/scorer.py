"""
ROLE005 — 单题评分 Agent（记录维度分与证据引用）。
"""

from __future__ import annotations

import json

from app.session.role.role005.agents._llm import invoke_llm_text
from app.session.role.role005.domain.models import ContextBundle
from app.session.role.role005.parsing import parse_json_object
from app.session.role.role_util.bindings import GraphBindings


def run_scorer_agent(
    bindings: GraphBindings,
    *,
    bundle: ContextBundle,
    student_text: str,
    evaluator_json: dict,
) -> tuple[dict, str]:
    """返回 scores 字典与 evidence_quotes。"""
    if evaluator_json.get("status") != "complete":
        return {}, "尚未完成作答，跳过评分"

    session = bundle.session
    plan = bundle.plan
    q_idx = session.current_question_index
    current = plan.questions[q_idx] if q_idx < len(plan.questions) else None
    if not current:
        return {}, "无当前题目"

    prompt = f"""你是面试评分器。本题已判定为完整回答，请按维度打分。

输出**仅一个** JSON：
{{"scores":{{"维度名":0-10}},"evidence_quotes":["学生原话摘录"],"summary":"一句评语"}}

题目：{current.text}
维度：{current.dimensions}
参考答案：{current.reference_answer}
学生回答：{student_text}
"""
    raw = invoke_llm_text(bindings, prompt)
    data, err = parse_json_object(raw)
    if err:
        return {}, err
    return data, ""
