"""
ROLE005 — 面试官 Agent。

红线
----
- 只提问、澄清、给思考方向；**禁止**评价好坏、禁止透露参考答案。
- Prompt 内大纲经 ``strip_reference_from_interviewer_context`` 剔除 reference_answer。
"""

from __future__ import annotations

import json

from app.session.role.role005.agents._llm import invoke_llm_text
from app.session.role.role005.infra.schema_gate import strip_reference_from_interviewer_context
from app.session.role.role005.domain.models import ContextBundle, InterviewPlan
from app.session.role.role005.parsing import normalize_interviewer_output, parse_json_object
from app.session.role.role_util.bindings import GraphBindings


def build_interviewer_prompt(
    bindings: GraphBindings,
    *,
    bundle: ContextBundle,
    turn_action: str,
    student_text: str,
) -> str:
    """根据回合动作构造面试官 Prompt。"""
    plan_view = strip_reference_from_interviewer_context(bundle.plan)
    session = bundle.session
    q_idx = session.current_question_index
    questions = plan_view.get("questions") or []
    current_q = questions[q_idx] if q_idx < len(questions) else {}

    action_hint = {
        "answer": "学生提交了回答，请根据 Evaluator 结论决定追问或进入下一题（输出 ask_followup 或 ask_question）。",
        "clarify": "学生对本题有疑问，请澄清题意，不要给答案（action=clarify）。",
        "hint": "学生请求提示，仅给思考方向（action=provide_hint，填 thinking_hint）。",
        "timeout": "本题超时，请给出温和鼓励性提示（action=provide_hint），不要跳过题目。",
        "start": "面试开始，请先进行自我介绍引导或第一题（phase=self_intro 时引导自我介绍）。",
        "resume": "学生重新进入或继续未完成题目，请直接提出当前题目（question_text 必填），可简短说明继续作答。",
    }.get(turn_action, "继续面试流程。")

    return f"""你是模拟面试官。严格遵守：
- 只提问/澄清/给思考提示，**禁止**评价好坏、禁止透露参考答案。
- 输出**仅一个** JSON 对象，字段含 action, question_id, question_text, thinking_hint, followup_text 等。

当前阶段：{session.phase}
当前题号索引：{q_idx}
当前题大纲：{json.dumps(current_q, ensure_ascii=False)}
完整大纲（无参考答案）：{json.dumps(plan_view, ensure_ascii=False)}
回合动作：{turn_action}
说明：{action_hint}
学生本轮输入：{student_text or "（无）"}

──角色约束──
{bindings.role_block}

输出 JSON，例如：
{{"action":"ask_question","question_id":"q1","question_text":"请介绍一个你主导的项目","thinking_hint":"可从背景、你的职责、结果三方面回答"}}
"""


def run_interviewer_agent(
    bindings: GraphBindings,
    *,
    bundle: ContextBundle,
    turn_action: str,
    student_text: str,
) -> tuple[dict, str]:
    """返回 (interviewer_json, error)。"""
    prompt = build_interviewer_prompt(
        bindings,
        bundle=bundle,
        turn_action=turn_action,
        student_text=student_text,
    )
    raw = invoke_llm_text(bindings, prompt, scenario="模拟面试-提问")
    data, err = parse_json_object(raw)
    if err:
        return {}, err
    return normalize_interviewer_output(data), ""
