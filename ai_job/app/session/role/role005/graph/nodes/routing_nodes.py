"""
ROLE005 — 答题图：路由、评估、评分节点。

- ``answer`` 动作走 evaluate → score → interviewer
- ``clarify/hint/timeout/start`` 跳过评估链，直达 interviewer
"""

from __future__ import annotations

from app.session.role.role005.agents.evaluator import run_evaluator_agent
from app.session.role.role005.agents.scorer import run_scorer_agent
from app.session.role.role005.domain.state import InterviewGraphState
from app.session.role.role005.graph.nodes._state_helpers import student_text
from app.session.role.role_util.bindings import GraphBindings, is_cancelled


def make_route_turn_node(bindings: GraphBindings):
    """入口节点：规范化 turn_action，供条件边使用。"""

    def node(state: InterviewGraphState) -> dict:
        if is_cancelled(bindings):
            return {"error": "已中止", "turn_action": state.turn_action}
        return {"turn_action": (state.turn_action or "answer").strip()}

    return node


def route_after_turn(state: InterviewGraphState) -> str:
    """
    条件路由函数名（LangGraph 第二个参数）。

    非 answer 类动作不经过 Evaluator，避免对空回答打分。
    """
    action = (state.turn_action or "answer").strip()
    if action in ("clarify", "hint", "timeout", "start", "resume", "abandon"):
        return "interviewer"
    return "evaluate"


def make_evaluate_node(bindings: GraphBindings):
    """Evaluator：判断回答是否 complete（可读 reference_answer）。"""

    def node(state: InterviewGraphState) -> dict:
        if is_cancelled(bindings) or not state.context:
            return {}
        text = student_text(state)
        if not text:
            # 无正文时直接标记 incomplete，由 Interviewer 追问
            return {
                "evaluator_json": {
                    "status": "incomplete",
                    "reason": "未收到回答内容",
                    "suggested_action": "followup",
                }
            }
        ev, _ = run_evaluator_agent(bindings, bundle=state.context, student_text=text)
        return {"evaluator_json": ev}

    return node


def make_score_node(bindings: GraphBindings):
    """Scorer：仅当 evaluator.status=complete 时写入维度分与 evidence。"""

    def node(state: InterviewGraphState) -> dict:
        if is_cancelled(bindings) or not state.context:
            return {}
        if state.evaluator_json.get("status") != "complete":
            return {}
        text = student_text(state)
        sc, _ = run_scorer_agent(
            bindings,
            bundle=state.context,
            student_text=text,
            evaluator_json=state.evaluator_json,
        )
        return {"scorer_json": sc}

    return node
