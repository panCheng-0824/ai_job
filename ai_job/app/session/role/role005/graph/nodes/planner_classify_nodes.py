"""
ROLE005 — 规划图：大纲行业两阶段分类节点。
"""

from __future__ import annotations

from app.session.role.role005.agents.plan_industry_classify import run_plan_industry_classify_agent
from app.session.role.role005.domain.state import PlannerGraphState
from app.session.role.role_util.bindings import GraphBindings, is_cancelled


def make_plan_industry_classify_node(bindings: GraphBindings):
    """工厂：Planner 产出大纲后，从 Redis 行业桶两阶段识别二级行业。"""

    def node(state: PlannerGraphState) -> dict:
        if is_cancelled(bindings) or state.error or state.plan is None:
            return {}
        if state.industry_classification is not None:
            return {}
        if state.plan.industry_category_id:
            return {}
        excerpt = (state.materials_text or "")[:2000]
        classification, err = run_plan_industry_classify_agent(
            bindings,
            plan=state.plan,
            target_role=state.target_role,
            materials_excerpt=excerpt,
        )
        if err or classification is None:
            return {"error": err or "行业分类失败"}
        updated_plan = state.plan.model_copy(
            update={"industry_category_id": classification.industry_category_id}
        )
        return {
            "industry_classification": classification,
            "plan": updated_plan,
        }

    return node
