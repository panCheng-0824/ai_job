"""
ROLE004 图编译与同步执行 — 简历优化师双通道。
"""

from __future__ import annotations

from app.session.role.role004.bindings import coerce_graph_state
from app.session.role.role004.nodes import (
    make_intent_router_node,
    make_resume_advise_node,
    make_resume_generate_node,
    route_after_intent_router,
)
from app.session.role.role004.resume_templates import DEFAULT_TEMPLATE_ID, get_template
from app.session.role.role004.state import ResumeOptimizeState
from app.session.role.role_util.bindings import GraphBindings


def compile_resume_optimize_graph(bindings: GraphBindings):
    """
    拓扑::

        intent_router ─┬─ resume_advise ──→ END
                       └─ resume_generate → END
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(ResumeOptimizeState)

    graph.add_node("intent_router", make_intent_router_node(bindings))
    graph.add_node("resume_advise", make_resume_advise_node(bindings))
    graph.add_node("resume_generate", make_resume_generate_node(bindings))

    graph.set_entry_point("intent_router")
    graph.add_conditional_edges(
        "intent_router",
        route_after_intent_router,
        {"advise": "resume_advise", "generate": "resume_generate"},
    )
    graph.add_edge("resume_advise", END)
    graph.add_edge("resume_generate", END)
    return graph.compile()


def run_resume_optimize_sync(
    question: str,
    *,
    bindings: GraphBindings,
    user_query: str = "",
    student_context: str = "",
    materials_block: str = "",
    template_id: str = "",
    intent: str = "",
    recursion_limit: int = 32,
) -> ResumeOptimizeState:
    """同步执行 ROLE004 完整图。"""
    compiled = compile_resume_optimize_graph(bindings)
    config = {"recursion_limit": recursion_limit}

    intent_norm = (intent or "").strip()
    if intent_norm not in ("resume_advise", "resume_generate"):
        intent_norm = ""

    tpl_id = get_template(template_id).id if (template_id or "").strip() else DEFAULT_TEMPLATE_ID

    initial = ResumeOptimizeState(
        question=question,
        user_query=(user_query or question).strip(),
        student_context=(student_context or "").strip(),
        materials_block=(materials_block or "").strip(),
        template_id=tpl_id,
        intent=intent_norm or "resume_advise",
    )
    output = compiled.invoke(initial, config=config)
    return coerce_graph_state(question, output)
