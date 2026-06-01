"""
ROLE005 — LLM 产物 Schema 门禁。

校验失败不得 silent pass，不得交由 server_job 入库。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Type

from pydantic import BaseModel, ValidationError

from app.session.role.role005.domain.models import (
    ContextBundle,
    InterviewPlan,
    InterviewReport,
    PlanPreviewResult,
    TurnResult,
)


def validate_model(model_cls: Type[BaseModel], data: Any) -> Tuple[BaseModel | None, str]:
    """校验并返回模型实例；失败返回 (None, 中文错误信息)。"""
    try:
        if isinstance(data, model_cls):
            return data, ""
        return model_cls.model_validate(data), ""
    except ValidationError as exc:
        return None, f"Schema 校验失败: {exc.errors()[:3]}"


def validate_interview_plan(data: Any) -> Tuple[InterviewPlan | None, str]:
    plan, err = validate_model(InterviewPlan, data)
    if err or plan is None:
        return None, err
    if not plan.questions:
        return None, "面试大纲至少需要一道题"
    return plan, ""


def validate_turn_result(data: Any) -> Tuple[TurnResult | None, str]:
    return validate_model(TurnResult, data)  # type: ignore[return-value]


def validate_context_bundle(data: Any) -> Tuple[ContextBundle | None, str]:
    return validate_model(ContextBundle, data)  # type: ignore[return-value]


def strip_reference_from_interviewer_context(plan: InterviewPlan) -> Dict[str, Any]:
    """
    生成供 Interviewer 使用的大纲视图（剔除 reference_answer）。

    防止参考答案泄漏到面试官 Prompt。
    """
    safe_questions: List[Dict[str, Any]] = []
    for q in plan.questions:
        d = q.model_dump(exclude={"reference_answer", "eval_criteria"})
        safe_questions.append(d)
    return {
        "plan_id": plan.plan_id,
        "version": plan.version,
        "target_role": plan.target_role,
        "questions": safe_questions,
    }
