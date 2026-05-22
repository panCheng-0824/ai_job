"""
ROLE001 图编译与同步执行。

图含入口意图路由器：岗位推荐快车道 vs 职业咨询 Plan-and-Execute 慢车道。
``langgraph`` 延迟导入，仅在跑岗位规划师流水线时加载。
"""

from __future__ import annotations

from app.session.role.role001.bindings import GraphBindings, coerce_graph_state
from app.session.role.role001.nodes import (
    make_executor_node,
    make_executor_router,
    make_intent_router_node,
    make_job_recommend_node,
    make_plain_finalize_node,
    make_planner_node,
    make_structured_return_node,
    route_after_intent_router,
)
from app.session.role.role001.state import JobPlanExecuteState


def compile_plan_execute_graph(bindings: GraphBindings):
    """
    组装并编译 StateGraph（含入口意图路由）。

    拓扑::

        intent_router ─┬─ job_recommend ──────────────────────────→ END
                       └─ planner → executor ⇄ executor
                            → structured_return | plain_finalize → END
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(JobPlanExecuteState)

    # --- 入口路由与快车道 ---
    graph.add_node("intent_router", make_intent_router_node(bindings))
    graph.add_node("job_recommend", make_job_recommend_node(bindings))

    # --- 咨询慢车道（Plan-and-Execute）---
    graph.add_node("planner", make_planner_node(bindings))
    graph.add_node("executor", make_executor_node(bindings))
    graph.add_node("structured_return", make_structured_return_node(bindings))
    graph.add_node("plain_finalize", make_plain_finalize_node(bindings))

    graph.set_entry_point("intent_router")
    graph.add_conditional_edges(
        "intent_router",
        route_after_intent_router,
        {"recommend": "job_recommend", "consult": "planner"},
    )
    graph.add_edge("job_recommend", END)

    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        make_executor_router(bindings),
        {"more": "executor", "structure": "structured_return", "plain": "plain_finalize"},
    )
    graph.add_edge("structured_return", END)
    graph.add_edge("plain_finalize", END)
    return graph.compile()


def run_job_plan_execute_sync(
    question: str,
    *,
    bindings: GraphBindings,
    user_query: str = "",
    student_context: str = "",
    intent: str = "",
    recursion_limit: int = 64,
) -> JobPlanExecuteState:
    """
    同步执行 ROLE001 完整图（含入口路由）。

    参数
    ----
    question:
        完整语境（系统提示 + 档案 + 历史 + 用户句），写入 ``state.question``。
    user_query:
        用户本轮原句；推荐快车道作为检索 query。
    student_context:
        学生档案摘要文本（通常来自 ``system_prompt_extra``）。
    intent:
        可选预分类（``job_recommend`` / ``career_consult``）；空则交由 ``intent_router`` 节点判定。
    """
    compiled = compile_plan_execute_graph(bindings)
    config = {"recursion_limit": recursion_limit}

    intent_norm = (intent or "").strip()
    if intent_norm not in ("job_recommend", "career_consult"):
        intent_norm = ""

    initial = JobPlanExecuteState(
        question=question,
        user_query=(user_query or question).strip(),
        student_context=(student_context or "").strip(),
        intent=intent_norm or "career_consult",
    )
    output = compiled.invoke(initial, config=config)
    return coerce_graph_state(question, output)
