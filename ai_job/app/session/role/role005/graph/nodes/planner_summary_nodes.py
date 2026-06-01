"""
ROLE005 — 规划图末尾：大纲摘要 + 题库 MQ 投递节点。
"""

from __future__ import annotations

from app.session.role.role005.agents.plan_summary import run_plan_summary_agent
from app.session.role.role005.domain.state import PlannerGraphState
from app.session.role.role005.mq.plan_bank import publish_plan_bank_result
from app.session.role.role_util.bindings import GraphBindings, is_cancelled


def make_plan_summary_node(bindings: GraphBindings):
    """
    工厂：根据已生成的大纲调用摘要 Agent。

    缓存命中时同样生成摘要（旧缓存可能无 summary），便于题库列表展示一致。
    """

    def node(state: PlannerGraphState) -> dict:
        if is_cancelled(bindings) or state.error or state.plan is None:
            return {}
        if state.plan_summary is not None:
            return {}
        excerpt = (state.materials_text or "")[:2000]
        summary, err = run_plan_summary_agent(
            bindings,
            plan=state.plan,
            target_role=state.target_role,
            materials_excerpt=excerpt,
        )
        if err or summary is None:
            return {"error": err or "大纲摘要生成失败"}
        return {"plan_summary": summary}

    return node


def make_publish_plan_mq_node(bindings: GraphBindings):
    """
    工厂：将大纲 + 摘要打包投递 ``interview.plan.result``。

    失败不阻断预览（写入 mq_error），由入口层决定是否向用户提示。
    """

    def node(state: PlannerGraphState) -> dict:
        if is_cancelled(bindings) or state.error or state.plan is None:
            return {}
        sent, mq_err = publish_plan_bank_result(
            student_id=state.student_id,
            material_hash=state.material_hash,
            target_role=state.target_role,
            plan=state.plan,
            plan_summary=state.plan_summary,
            industry_classification=state.industry_classification,
            cache_meta=state.cache_meta,
        )
        return {"mq_published": sent, "mq_error": mq_err or ""}

    return node
