"""
ROLE005 — 回答评估 Agent。

与 Interviewer 隔离：本 Agent **可读** reference_answer 与 eval_criteria，
产出 complete / incomplete / need_clarification，驱动是否进入 Scorer。
"""

from __future__ import annotations

import json

from app.session.role.role005.agents._llm import invoke_llm_text
from app.session.role.role005.domain.models import ContextBundle
from app.session.role.role005.parsing import parse_json_object
from app.session.role.role_util.bindings import GraphBindings


def run_evaluator_agent(
    bindings: GraphBindings,
    *,
    bundle: ContextBundle,
    student_text: str,
) -> tuple[dict, str]:
    """
    评估学生回答是否完整。

    返回 JSON 含：status(complete|incomplete|need_clarification), reason, suggested_action
    """
    session = bundle.session
    plan = bundle.plan
    q_idx = session.current_question_index
    questions = plan.questions
    current = questions[q_idx] if q_idx < len(questions) else None
    ref = (current.reference_answer if current else "") or ""

    prompt = f"""你是面试回答评估器（学生不可见）。根据参考答案与评分要点，判断回答是否充分。

输出**仅一个** JSON：
{{"status":"complete|incomplete|need_clarification","reason":"...","suggested_action":"followup|next_question|clarify"}}

当前题：{current.text if current else ""}
参考答案（内部）：{ref}
评分要点：{json.dumps(current.eval_criteria if current else {}, ensure_ascii=False)}
学生回答：{student_text}

──角色约束──
{bindings.role_block}
"""
    raw = invoke_llm_text(bindings, prompt)
    data, err = parse_json_object(raw)
    if err:
        return {"status": "incomplete", "reason": err, "suggested_action": "followup"}, ""
    status = str(data.get("status") or "incomplete").strip()
    if status not in ("complete", "incomplete", "need_clarification"):
        status = "incomplete"
    data["status"] = status
    return data, ""
