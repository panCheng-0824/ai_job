"""
ROLE005 — 面试大纲规划图（同步 LangGraph）。

职责
----
- ``compile_planner_graph``：注册规划阶段节点并编译为可执行图；
- ``run_plan_preview_sync``：供 SSE ``plan_preview``、内部 API、dev 联调同步调用。

与答题图 ``interview_graph`` 分离：本图只在「面试开始前」生成 ``InterviewPlan``（题目列表），
不提问、不评分；正式逐轮面试走 ``compile_interview_turn_graph``。

规划拓扑含 ``plan_industry_classify``：先从 Redis ``top_category`` 识别一级行业，
再按一级 id 读取二级桶完成绑定，避免全量类目导致 LLM 注意力丢失。
"""

from __future__ import annotations

from app.session.role.role005.bindings import coerce_planner_state
from app.session.role.role005.domain.models import PlanPreviewResult
from app.session.role.role005.domain.state import PlannerGraphState
from app.session.role.role005.graph.nodes.planner_nodes import (
    make_extract_materials_node,
    make_plan_cache_node,
    make_planner_llm_node,
)
from app.session.role.role005.graph.nodes.planner_classify_nodes import (
    make_plan_industry_classify_node,
)
from app.session.role.role005.graph.nodes.planner_summary_nodes import (
    make_plan_summary_node,
    make_publish_plan_mq_node,
)
from app.session.role.role_util.bindings import GraphBindings


def compile_planner_graph(bindings: GraphBindings):
    """
    编译「素材 → 缓存 → LLM 规划 → 摘要 → MQ 题库」线性图。

    拓扑
    ----
    extract_materials → plan_cache → planner_llm → plan_industry_classify
        → plan_summary → publish_plan_mq → END
    """
    from langgraph.graph import END, StateGraph

    graph = StateGraph(PlannerGraphState)

    graph.add_node("extract_materials", make_extract_materials_node(bindings))
    graph.add_node("plan_cache", make_plan_cache_node(bindings))
    graph.add_node("planner_llm", make_planner_llm_node(bindings))
    graph.add_node(
        "plan_industry_classify",
        make_plan_industry_classify_node(bindings),
    )
    graph.add_node("plan_summary", make_plan_summary_node(bindings))
    graph.add_node("publish_plan_mq", make_publish_plan_mq_node(bindings))

    graph.set_entry_point("extract_materials")
    graph.add_edge("extract_materials", "plan_cache")
    graph.add_edge("plan_cache", "planner_llm")
    graph.add_edge("planner_llm", "plan_industry_classify")
    graph.add_edge("plan_industry_classify", "plan_summary")
    graph.add_edge("plan_summary", "publish_plan_mq")
    graph.add_edge("publish_plan_mq", END)
    return graph.compile()


def run_plan_preview_sync(
    *,
    bindings: GraphBindings,
    materials_block: str,
    material_hash: str,
    target_role: str,
    student_context: str = "",
    student_id: str = "",
    session_id: str = "",
    recursion_limit: int = 24,
) -> PlanPreviewResult:
    """
    同步跑完整张规划图，返回大纲预览结果（含摘要与 MQ 投递状态）。

    参数
    ----
    student_id:
        学号，写入 MQ payload 供 server_job 写入 ``interview_plan_basics.student_id``。
    """
    compiled = compile_planner_graph(bindings)
    initial = PlannerGraphState(
        materials_text=materials_block,
        material_hash=material_hash,
        target_role=target_role,
        student_context=student_context,
        student_id=(student_id or "").strip(),
        session_id=(session_id or "").strip(),
    )
    out = compiled.invoke(initial, config={"recursion_limit": recursion_limit})
    state = coerce_planner_state(out)
    if state.error or state.plan is None:
        raise RuntimeError(state.error or "未能生成面试大纲")
    return PlanPreviewResult(
        plan=state.plan,
        plan_summary=state.plan_summary,
        industry_classification=state.industry_classification,
        cache_meta=state.cache_meta,
        material_hash=material_hash,
        mq_published=state.mq_published,
        mq_error=state.mq_error,
    )
