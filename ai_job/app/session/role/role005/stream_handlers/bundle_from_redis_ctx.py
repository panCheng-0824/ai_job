"""
ROLE005 — 由 Redis 整场 ctx 构造答题图所需的 ContextBundle。

不调用 server_job；题目与进度均来自 server 写入的 Redis 快照。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.session.role.role005.domain.models import (
    ContextBundle,
    InterviewPlan,
    InterviewSessionSnapshot,
    QuestionItem,
)


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _question_from_snap(snap: Dict[str, Any]) -> QuestionItem:
    """Redis 题目快照 → QuestionItem。"""
    qid = str(snap.get("id") or snap.get("question_id") or "").strip() or "q1"
    return QuestionItem(
        id=qid,
        text=str(snap.get("text") or snap.get("question_text") or "").strip(),
        dimensions=list(snap.get("dimensions") or []),
        weight=float(snap.get("weight") or 1.0),
        thinking_hint=str(snap.get("thinking_hint") or "").strip(),
        timeout_seconds=_to_int(snap.get("timeout_seconds"), 300),
        preset_followups=list(snap.get("preset_followups") or []),
        reference_answer=str(snap.get("reference_answer") or "").strip(),
        eval_criteria=dict(snap.get("eval_criteria") or {}),
    )


def build_context_bundle_from_redis_ctx(redis_ctx: Dict[str, Any]) -> ContextBundle:
    """
    将 ``interview:ctx`` JSON 转为 ContextBundle。

    要求 redis_ctx 含 server 写入的 ``questions`` 列表与 ``current_question_index``。
    """
    questions_raw = redis_ctx.get("questions")
    items: List[QuestionItem] = []
    if isinstance(questions_raw, list) and questions_raw:
        for row in questions_raw:
            if isinstance(row, dict):
                items.append(_question_from_snap(row))
    elif isinstance(redis_ctx.get("current_question"), dict):
        # 旧版 ctx 无 questions 列表时，仅用当前题兜底
        items.append(_question_from_snap(redis_ctx["current_question"]))

    idx = _to_int(redis_ctx.get("current_question_index"), 0)
    session = InterviewSessionSnapshot(
        interview_session_id=str(redis_ctx.get("interview_session_id") or "").strip(),
        student_id=str(redis_ctx.get("student_id") or "").strip(),
        plan_id=str(redis_ctx.get("plan_id") or "").strip(),
        plan_version=_to_int(redis_ctx.get("plan_version"), 1),
        status=str(redis_ctx.get("status") or "in_progress").strip(),
        phase=str(redis_ctx.get("phase") or "question").strip(),
        current_question_index=idx,
        snapshots={},
    )
    plan = InterviewPlan(
        plan_id=session.plan_id or "plan_unknown",
        version=session.plan_version,
        target_role=str(redis_ctx.get("target_role") or "").strip(),
        questions=items,
    )
    return ContextBundle(session=session, plan=plan, student_profile={})
