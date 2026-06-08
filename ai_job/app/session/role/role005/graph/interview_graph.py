"""
ROLE005 — 单轮 /turn 答题图（同步）。
"""

from __future__ import annotations

from app.session.role.role005.bindings import coerce_interview_state
from app.session.role.role005.domain.models import ContextBundle, TurnResult
from app.session.role.role005.domain.state import InterviewGraphState
from app.session.role.role005.graph.nodes.interview_nodes import (
    make_evaluate_node,
    make_finalize_turn_node,
    make_interviewer_node,
    make_route_turn_node,
    make_score_node,
    route_after_turn,
)
from app.session.role.role005.infra.checkpoint import (
    extract_checkpoint_id,
    get_interview_checkpointer,
    interview_turn_thread_config,
)
from app.session.role.role_util.bindings import GraphBindings


def compile_interview_turn_graph(bindings: GraphBindings):
    """
    拓扑::

        route_turn ─┬─ evaluate → score ─┐
                    └─ interviewer ◄────┘
                              ↓
                         finalize → END

    若 Redis checkpointer 可用，各节点执行后自动写入 ShallowRedisSaver。
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(InterviewGraphState)
    graph.add_node("route_turn", make_route_turn_node(bindings))
    graph.add_node("evaluate", make_evaluate_node(bindings))
    graph.add_node("score", make_score_node(bindings))
    graph.add_node("interviewer", make_interviewer_node(bindings))
    graph.add_node("finalize", make_finalize_turn_node(bindings))

    graph.set_entry_point("route_turn")
    graph.add_conditional_edges(
        "route_turn",
        route_after_turn,
        {"evaluate": "evaluate", "interviewer": "interviewer"},
    )
    graph.add_edge("evaluate", "score")
    graph.add_edge("score", "interviewer")
    graph.add_edge("interviewer", "finalize")
    graph.add_edge("finalize", END)

    checkpointer = get_interview_checkpointer()
    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


def run_interview_turn_sync(
    *,
    bindings: GraphBindings,
    context: ContextBundle,
    turn_action: str,
    turn_payload: dict,
    user_query: str = "",
    recursion_limit: int = 24,
) -> TurnResult:
    """同步执行单轮 turn，返回结构化 TurnResult。"""
    compiled = compile_interview_turn_graph(bindings)
    config = interview_turn_thread_config(
        context.session.interview_session_id,
        recursion_limit=recursion_limit,
    )
    initial = InterviewGraphState(
        context=context,
        turn_action=(turn_action or "answer").strip(),
        turn_payload=dict(turn_payload or {}),
        user_query=(user_query or "").strip(),
        question_index=context.session.current_question_index,
    )
    out = compiled.invoke(initial, config=config)
    state = coerce_interview_state(out)
    if state.error:
        raise RuntimeError(state.error)
    if state.turn_result:
        turn_result = TurnResult.model_validate(state.turn_result)
        if get_interview_checkpointer() is not None:
            checkpoint_id = extract_checkpoint_id(compiled.get_state(config))
            if checkpoint_id:
                turn_result = turn_result.model_copy(
                    update={"checkpoint_id": checkpoint_id}
                )
        return turn_result
    raise RuntimeError("turn 未产生结果")
