"""
ROLE005 — 从 Redis ctx 解析「下一道待作答题」并校准进度指针。

重新进入遮层时，按 ``seq_no`` 升序取第一道 ``answer_status`` 未完结的题。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

_COMPLETED = frozenset({"completed", "answered", "summarized"})


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


def _is_completed(status: Any) -> bool:
    return str(status or "pending").strip().lower() in _COMPLETED


def sorted_question_snaps(redis_ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """ctx.questions 按 seq_no 升序。"""
    raw = redis_ctx.get("questions")
    if not isinstance(raw, list):
        return []
    snaps = [q for q in raw if isinstance(q, dict)]
    return sorted(snaps, key=lambda q: _to_int(q.get("seq_no"), 0))


def find_first_incomplete_question(redis_ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    按排序返回第一道未完结题目快照。

    未完结：``answer_status`` 不在 completed / answered / summarized。
    """
    for q in sorted_question_snaps(redis_ctx):
        if not _is_completed(q.get("answer_status")):
            return q
    return None


def apply_active_question_to_ctx(
    redis_ctx: Dict[str, Any],
    active: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    """
    将 active 题写入 ctx 指针字段，返回 (新 ctx, 在 questions 列表中的 index)。
    """
    out = copy.deepcopy(redis_ctx)
    snaps = sorted_question_snaps(out)
    active_seq = _to_int(active.get("seq_no"), 0)
    active_id = str(active.get("id") or active.get("question_id") or "").strip()

    list_index = 0
    for i, q in enumerate(snaps):
        if _to_int(q.get("seq_no"), -1) == active_seq:
            list_index = i
            break
        if active_id and str(q.get("id") or "") == active_id:
            list_index = i
            break

    out["current_question_index"] = list_index
    out["current_seq_no"] = active_seq
    out["current_question_id"] = active_id or str(active.get("id") or "")
    out["current_question"] = active
    if active_seq > 0 or str(out.get("phase") or "") not in ("", "ready", "self_intro"):
        out["phase"] = "question"
    if str(out.get("status") or "") == "ready":
        out["status"] = "in_progress"
    return out, list_index


def resolve_active_for_answer(
    redis_ctx: Dict[str, Any],
    turn_ctx: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    答题回合：优先 turn_ctx / Redis 当前指针，且该题未完结；否则取第一道未作答题。
    """
    snaps = sorted_question_snaps(redis_ctx)
    qid = str(turn_ctx.get("question_id") or redis_ctx.get("current_question_id") or "").strip()
    seq = turn_ctx.get("seq_no")
    if seq is None:
        seq = redis_ctx.get("current_seq_no")
    for q in snaps:
        if _is_completed(q.get("answer_status")):
            continue
        if qid and str(q.get("id") or q.get("question_id") or "") == qid:
            return q
        if seq is not None and _to_int(q.get("seq_no"), -1) == _to_int(seq, -2):
            return q
    return find_first_incomplete_question(redis_ctx)


def resolve_resume_for_enter(redis_ctx: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    进入/重新进入遮层：定位待作答题并决定 turn_action。

    返回 (校准后的 ctx, active 题快照, turn_action)。
    """
    active = find_first_incomplete_question(redis_ctx)
    if active is None:
        return redis_ctx, {}, "answer"
    patched, _ = apply_active_question_to_ctx(redis_ctx, active)
    action = resolve_enter_turn_action(patched, active)
    return patched, active, action


def resolve_enter_turn_action(redis_ctx: Dict[str, Any], active: Dict[str, Any]) -> str:
    """
    首次开场用 ``start``；已有进度或重进未完成题用 ``resume``。
    """
    seq = _to_int(active.get("seq_no"), 0)
    phase = str(redis_ctx.get("phase") or "").strip()
    answered = _to_int(redis_ctx.get("question_answered"), 0)
    if (
        seq == 0
        and answered == 0
        and phase in ("", "ready", "self_intro")
        and not _is_completed(active.get("answer_status"))
        and str(active.get("answer_status") or "pending").lower() == "pending"
    ):
        return "start"
    return "resume"


def patch_ctx_after_question_completed(
    redis_ctx: Dict[str, Any],
    completed_seq_no: int,
) -> Dict[str, Any]:
    """
    将本题标记 completed 并推进 ctx 指针（与 server advanceAfterQuestionCompleted 语义对齐）。

    若该题已是 completed（MQ 已消费），仅校准指针，不重复累加 question_answered。
    """
    patched = copy.deepcopy(redis_ctx)
    snaps = sorted_question_snaps(patched)
    if not snaps:
        return patched

    target = None
    for q in snaps:
        if _to_int(q.get("seq_no"), -1) == completed_seq_no:
            target = q
            break

    if target is None:
        return patched

    if _is_completed(target.get("answer_status")):
        next_active = find_first_incomplete_question({"questions": snaps})
        if next_active is None:
            patched["status"] = "completed"
            patched["phase"] = "completed"
        else:
            patched, _ = apply_active_question_to_ctx(patched, next_active)
            patched["status"] = "in_progress"
            patched["phase"] = "question"
        patched["questions"] = snaps
        return patched

    target["answer_status"] = "completed"
    patched["question_answered"] = _to_int(patched.get("question_answered"), 0) + 1
    patched["status"] = "in_progress"
    patched["phase"] = "question"

    # 与 server applyCompletedAt 对齐：下一题 seq 标记 in_progress
    next_seq = completed_seq_no + 1
    for q in snaps:
        if _to_int(q.get("seq_no"), -1) == next_seq:
            q["answer_status"] = "in_progress"
            break

    next_active = find_first_incomplete_question({"questions": snaps})
    if next_active is None:
        patched["status"] = "completed"
        patched["phase"] = "completed"
        patched["current_question_index"] = len(snaps)
        patched["current_seq_no"] = len(snaps)
        patched["current_question_id"] = ""
        patched["current_iq_row_id"] = ""
        patched["current_question"] = {}
    else:
        patched, _ = apply_active_question_to_ctx(patched, next_active)

    patched["questions"] = snaps
    return patched


def build_progress_from_patched_ctx(
    patched_ctx: Dict[str, Any],
    *,
    record_id: str,
    interview_session_id: str,
    question_advanced: bool = False,
    evaluator_status: str = "",
) -> Dict[str, Any]:
    """由写回后的 ctx 构造 interview_progress SSE 载荷。"""
    return {
        "mode": "interview",
        "record_id": record_id,
        "interview_session_id": interview_session_id,
        "phase": patched_ctx.get("phase") or "question",
        "status": patched_ctx.get("status") or "in_progress",
        "current_question_index": patched_ctx.get("current_question_index"),
        "seq_no": patched_ctx.get("current_seq_no"),
        "question_id": patched_ctx.get("current_question_id") or "",
        "question_session_key": "",
        "question_total": patched_ctx.get("question_total"),
        "question_answered": patched_ctx.get("question_answered"),
        "evaluator_status": evaluator_status,
        "question_advanced": question_advanced,
        "current_question_text": _text_from_current_question(patched_ctx),
    }


def _text_from_current_question(ctx: Dict[str, Any]) -> str:
    current = ctx.get("current_question")
    if isinstance(current, dict):
        return str(current.get("text") or "").strip()
    return ""


def build_progress_after_question_advanced(
    redis_ctx: Dict[str, Any],
    completed_seq_no: int,
    *,
    record_id: str,
    interview_session_id: str,
) -> Optional[Dict[str, Any]]:
    """
    本地推算下一题 progress（不写 Redis；写 Redis 请用 patch + save）。

    保留供单测与未发送 MQ 时的降级。
    """
    patched = patch_ctx_after_question_completed(redis_ctx, completed_seq_no)
    return build_progress_from_patched_ctx(
        patched,
        record_id=record_id,
        interview_session_id=interview_session_id,
        question_advanced=True,
        evaluator_status="complete",
    )
