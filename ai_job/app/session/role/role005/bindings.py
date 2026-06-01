"""
ROLE005 — LangGraph 运行时绑定组装与状态 coercion。

- ``build_graph_bindings``：SSE / 内部 API 共用
- ``coerce_*``：将图 invoke 返回值统一为 dataclass 状态
"""

from __future__ import annotations

from threading import Event
from typing import Any, Dict

from app.session.role.role005.domain.models import (
    ContextBundle,
    InterviewPlan,
    PlanIndustryClassification,
    PlanSummary,
)
from app.session.role.role005.domain.state import InterviewGraphState, PlannerGraphState
from app.session.role.role_util.bindings import GraphBindings
from app.session.role.role_util.config import build_role_block, tools_from_user_model


def build_graph_bindings(
    merged_user: Dict[str, Any],
    llm: Any,
    cancel_event: Event,
    *,
    history_block: str = "",
) -> GraphBindings:
    """
    组装 LangGraph 节点所需的只读依赖。

    参数
    ----
    merged_user:
        合并后的 usermodel（含 user_profile、tools、model_level）。
    llm:
        已配置超时与温度的 ChatModel 实例。
    cancel_event:
        客户端中止 SSE 时置位，节点内通过 ``is_cancelled`` 检查。
    """
    role_block = build_role_block(merged_user)
    identity = {
        "username": merged_user.get("username", ""),
        "usercode": merged_user.get("usercode", ""),
        "output_format": merged_user.get("output_format", ""),
        "model_level": merged_user.get("model_level", ""),
    }
    tools, tool_map = tools_from_user_model(merged_user)
    return GraphBindings(
        llm=llm,
        cancel_event=cancel_event,
        role_block=role_block,
        identity=identity,
        tools=tools,
        tool_map=tool_map,
        use_structured_return=True,
        history_block=history_block,
    )


def coerce_planner_state(data: Any) -> PlannerGraphState:
    """将 LangGraph ``invoke`` 返回值统一为 ``PlannerGraphState``。"""
    if isinstance(data, PlannerGraphState):
        return data
    if isinstance(data, dict):
        plan = data.get("plan")
        if plan is not None and not isinstance(plan, InterviewPlan):
            try:
                plan = InterviewPlan.model_validate(plan)
            except Exception:
                plan = None
        plan_summary = data.get("plan_summary")
        if plan_summary is not None and not isinstance(plan_summary, PlanSummary):
            try:
                plan_summary = PlanSummary.model_validate(plan_summary)
            except Exception:
                plan_summary = None
        industry_classification = data.get("industry_classification")
        if industry_classification is not None and not isinstance(
            industry_classification, PlanIndustryClassification
        ):
            try:
                industry_classification = PlanIndustryClassification.model_validate(
                    industry_classification
                )
            except Exception:
                industry_classification = None
        return PlannerGraphState(
            materials_text=str(data.get("materials_text") or ""),
            material_hash=str(data.get("material_hash") or ""),
            target_role=str(data.get("target_role") or ""),
            student_context=str(data.get("student_context") or ""),
            student_id=str(data.get("student_id") or ""),
            plan=plan,
            industry_classification=industry_classification,
            plan_summary=plan_summary,
            cache_meta=dict(data.get("cache_meta") or {}),
            mq_published=bool(data.get("mq_published")),
            mq_error=str(data.get("mq_error") or ""),
            error=str(data.get("error") or ""),
        )
    raise TypeError(f"无法解析 Planner 图状态: {type(data)!r}")


def coerce_interview_state(data: Any) -> InterviewGraphState:
    """将 LangGraph ``invoke`` 返回值统一为 ``InterviewGraphState``。"""
    if isinstance(data, InterviewGraphState):
        return data
    if isinstance(data, dict):
        ctx = data.get("context")
        if ctx is not None and not isinstance(ctx, ContextBundle):
            try:
                ctx = ContextBundle.model_validate(ctx)
            except Exception:
                ctx = None
        return InterviewGraphState(
            context=ctx,
            turn_action=str(data.get("turn_action") or "answer"),
            turn_payload=dict(data.get("turn_payload") or {}),
            user_query=str(data.get("user_query") or ""),
            question_index=int(data.get("question_index") or 0),
            interviewer_json=dict(data.get("interviewer_json") or {}),
            evaluator_json=dict(data.get("evaluator_json") or {}),
            scorer_json=dict(data.get("scorer_json") or {}),
            clarifier_text=str(data.get("clarifier_text") or ""),
            final_answer=str(data.get("final_answer") or ""),
            turn_result=dict(data.get("turn_result") or {}),
            token_usage=dict(data.get("token_usage") or {}),
            error=str(data.get("error") or ""),
        )
    raise TypeError(f"无法解析 Interview 图状态: {type(data)!r}")
