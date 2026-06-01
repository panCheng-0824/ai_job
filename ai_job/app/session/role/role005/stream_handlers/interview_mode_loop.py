"""
ROLE005 — 遮层面试模式 SSE（start / answer 单题多轮深挖）。

进度与题目快照只读 Redis（``interview:ctx`` / ``interview:qsess``），不调用 server_job HTTP。
重新进入时按 ``seq_no`` 取第一道未作答题继续。
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Iterator

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role005.graph.interview_graph import run_interview_turn_sync
from app.session.role.role005.infra.interview_ctx_redis import (
    load_interview_ctx,
    optimistic_advance_after_question_complete,
)
from app.session.role.role005.infra.interview_qsess_redis import (
    append_qsess_turn,
    delete_qsess,
    save_qsess,
)
from app.session.role.role005.materials.interview_mode import build_question_session_key
from app.session.role.role005.mq.question_completed import publish_question_completed
from app.session.role.role005.parsing import interviewer_display_text
from app.session.role.role005.stream_handlers.bundle_from_redis_ctx import (
    build_context_bundle_from_redis_ctx,
)
from app.session.role.role005.stream_handlers.interview_ctx_resume import (
    apply_active_question_to_ctx,
    build_progress_from_patched_ctx,
    find_first_incomplete_question,
    resolve_active_for_answer,
    resolve_resume_for_enter,
)
from app.session.role.role_util.bindings import GraphBindings
from app.session.role.role_util.stream_common import chunk_text


def _student_answer_text(question: str, turn_ctx: Dict[str, Any]) -> str:
    """从用户可见消息或 payload 取本轮回答正文。"""
    payload = turn_ctx.get("payload") if isinstance(turn_ctx.get("payload"), dict) else {}
    from_payload = str(payload.get("answer_text") or "").strip()
    if from_payload:
        return from_payload
    return (question or "").strip()


def _merge_turn_ctx_from_redis(turn_ctx: Dict[str, Any], redis_ctx: Dict[str, Any]) -> None:
    """用 Redis ctx 补全 turn_ctx 中缺失的进度字段（原地修改）。"""
    if not turn_ctx.get("interview_session_id") and redis_ctx.get("interview_session_id"):
        turn_ctx["interview_session_id"] = str(redis_ctx.get("interview_session_id"))
    if not turn_ctx.get("question_id") and redis_ctx.get("current_question_id"):
        turn_ctx["question_id"] = str(redis_ctx.get("current_question_id"))
    if turn_ctx.get("seq_no") is None and redis_ctx.get("current_seq_no") is not None:
        turn_ctx["seq_no"] = redis_ctx.get("current_seq_no")
    if not turn_ctx.get("chat_session_id") and redis_ctx.get("chat_session_id"):
        turn_ctx["chat_session_id"] = str(redis_ctx.get("chat_session_id"))


def _sync_turn_ctx_from_active(turn_ctx: Dict[str, Any], active: Dict[str, Any]) -> None:
    """将待作答题快照写入 turn_ctx。"""
    if not active:
        return
    qid = str(active.get("id") or active.get("question_id") or "").strip()
    if qid:
        turn_ctx["question_id"] = qid
    if active.get("seq_no") is not None:
        turn_ctx["seq_no"] = active.get("seq_no")


def _resolve_qsess_key(turn_ctx: Dict[str, Any], redis_ctx: Dict[str, Any]) -> str:
    """优先 message_context 指定 key，否则按当前题构造。"""
    explicit = str(turn_ctx.get("question_session_key") or "").strip()
    if explicit:
        return explicit
    return build_question_session_key(
        str(turn_ctx.get("chat_session_id") or redis_ctx.get("chat_session_id") or ""),
        str(turn_ctx.get("student_id") or redis_ctx.get("student_id") or ""),
        str(turn_ctx.get("record_id") or redis_ctx.get("record_id") or ""),
        str(turn_ctx.get("question_id") or redis_ctx.get("current_question_id") or ""),
    )


def _build_progress_payload(
    *,
    redis_ctx: Dict[str, Any],
    turn_ctx: Dict[str, Any],
    turn_result: Any,
    qsess_key: str,
    question_advanced: bool = False,
) -> Dict[str, Any]:
    list_index = redis_ctx.get("current_question_index")
    if list_index is None:
        list_index = turn_result.current_question_index
    return {
        "mode": "interview",
        "record_id": str(turn_ctx.get("record_id") or redis_ctx.get("record_id") or ""),
        "interview_session_id": turn_result.interview_session_id,
        "phase": redis_ctx.get("phase") or turn_result.phase,
        "current_question_index": list_index,
        "question_session_key": qsess_key,
        "question_id": turn_ctx.get("question_id"),
        "seq_no": turn_ctx.get("seq_no"),
        "question_total": redis_ctx.get("question_total"),
        "question_answered": redis_ctx.get("question_answered"),
        "evaluator_status": (turn_result.evaluator_output or {}).get("status"),
        "current_question_text": _question_text_from_redis(redis_ctx, turn_ctx),
        "question_advanced": question_advanced,
    }


def _maybe_publish_question_complete(
    *,
    turn_ctx: Dict[str, Any],
    redis_ctx: Dict[str, Any],
    turn_result: Any,
    answer_text: str,
    qsess_key: str,
) -> tuple[bool, str]:
    """evaluator complete 时投递 MQ 并清理 qsess。"""
    ev = turn_result.evaluator_output or {}
    if str(ev.get("status") or "").strip() != "complete":
        return False, ""
    seq_no = turn_ctx.get("seq_no")
    if seq_no is None:
        seq_no = redis_ctx.get("current_seq_no", 0)
    try:
        seq_no = int(seq_no)
    except (TypeError, ValueError):
        seq_no = 0
    sent, err = publish_question_completed(
        student_id=str(turn_ctx.get("student_id") or redis_ctx.get("student_id") or ""),
        record_id=str(turn_ctx.get("record_id") or redis_ctx.get("record_id") or ""),
        interview_session_id=str(
            turn_ctx.get("interview_session_id") or redis_ctx.get("interview_session_id") or ""
        ),
        question_id=str(turn_ctx.get("question_id") or redis_ctx.get("current_question_id") or ""),
        seq_no=seq_no,
        answer_text=answer_text,
        evaluator_json=ev,
        scorer_json=turn_result.scorer_output or {},
        turn_id=str(uuid.uuid4()),
    )
    if sent:
        delete_qsess(qsess_key)
    return sent, err


def iter_interview_mode_tokens(
    bindings: GraphBindings,
    *,
    ctx: ChatStreamRunContext,
    turn_ctx: Dict[str, Any],
    question: str,
    student_id: str,
    role_label: str,
    is_start: bool,
) -> Iterator[Dict[str, str]]:
    """
    遮层面试：读 Redis ctx → 定位未作答题 → 单题 qsess → 答题图 → 题完结发 MQ。
    """
    record_id = str(turn_ctx.get("record_id") or "").strip()
    sid = str(turn_ctx.get("student_id") or student_id or "").strip()
    if not record_id or not sid:
        yield {"type": "answer", "content": "缺少 record_id / student_id，无法进入面试模式。"}
        return

    redis_ctx = load_interview_ctx(
        student_id=sid,
        record_id=record_id,
        ctx_key=str(turn_ctx.get("ctx_key") or ""),
    )
    if not redis_ctx:
        yield {
            "type": "answer",
            "content": "未找到面试进度（Redis ctx 不存在或已过期），请重新开始或联系管理员。",
        }
        return

    ctx_owner = str(redis_ctx.get("student_id") or "").strip()
    if ctx_owner and ctx_owner != sid:
        yield {"type": "answer", "content": "面试记录与当前学号不匹配，无法继续。"}
        return

    if str(redis_ctx.get("status") or "").strip() == "completed":
        yield {"type": "answer", "content": "本场面试已全部完成，可在「我的面试记录」查看详情。"}
        return

    if is_start:
        active = find_first_incomplete_question(redis_ctx)
        if active is None:
            yield {"type": "answer", "content": "所有题目均已完成，可在「我的面试记录」查看详情。"}
            return
        redis_ctx, active, turn_action = resolve_resume_for_enter(redis_ctx)
    else:
        active = resolve_active_for_answer(redis_ctx, turn_ctx)
        if active is None:
            yield {"type": "answer", "content": "所有题目均已完成，可在「我的面试记录」查看详情。"}
            return
        redis_ctx, _ = apply_active_question_to_ctx(redis_ctx, active)
        turn_action = "answer"

    _sync_turn_ctx_from_active(turn_ctx, active)
    _merge_turn_ctx_from_redis(turn_ctx, redis_ctx)
    turn_ctx["action"] = turn_action

    payload: Dict[str, Any] = {}
    if not is_start:
        payload["answer_text"] = _student_answer_text(question, turn_ctx)
        turn_ctx["payload"] = payload

    qsess_key = _resolve_qsess_key(turn_ctx, redis_ctx)
    turn_ctx["question_session_key"] = qsess_key

    yield {
        "type": "thinking",
        "content": (
            f"【{role_label}·遮层面试】record={record_id} "
            f"action={turn_action} seq={turn_ctx.get('seq_no')} qsess={qsess_key[-32:]}\n"
        ),
    }

    bundle = build_context_bundle_from_redis_ctx(redis_ctx)
    turn_result = run_interview_turn_sync(
        bindings=bindings,
        context=bundle,
        turn_action=turn_action,
        turn_payload=payload,
        user_query=question if not is_start else "",
    )

    display = turn_result.final_answer_text or interviewer_display_text(
        turn_result.interviewer_output or {}
    )
    if is_start:
        qsess = {
            "record_id": record_id,
            "question_id": turn_ctx.get("question_id"),
            "seq_no": turn_ctx.get("seq_no"),
            "turns": [{"role": "interviewer", "text": display}],
        }
        save_qsess(qsess_key, qsess)
    else:
        answer_text = payload.get("answer_text", "")
        append_qsess_turn(qsess_key, role="student", text=answer_text)
        append_qsess_turn(qsess_key, role="interviewer", text=display)

    progress = _build_progress_payload(
        redis_ctx=redis_ctx,
        turn_ctx=turn_ctx,
        turn_result=turn_result,
        qsess_key=qsess_key,
    )
    yield {
        "type": "interview_progress",
        "content": json.dumps(progress, ensure_ascii=False),
    }

    mq_sent, mq_err = _maybe_publish_question_complete(
        turn_ctx=turn_ctx,
        redis_ctx=redis_ctx,
        turn_result=turn_result,
        answer_text=payload.get("answer_text", "") if not is_start else "",
        qsess_key=qsess_key,
    )
    if mq_sent:
        yield {
            "type": "thinking",
            "content": f"【{role_label}】本题已完结，结果已投递 MQ。\n",
        }
        try:
            completed_seq = int(turn_ctx.get("seq_no", 0))
        except (TypeError, ValueError):
            completed_seq = 0
        # MQ 发送成功后乐观写回 Redis，避免消费延迟导致重复答题
        patched_ctx = optimistic_advance_after_question_complete(
            student_id=sid,
            record_id=record_id,
            completed_seq_no=completed_seq,
            ctx_key=str(turn_ctx.get("ctx_key") or ""),
        )
        if patched_ctx:
            advanced = build_progress_from_patched_ctx(
                patched_ctx,
                record_id=record_id,
                interview_session_id=str(turn_result.interview_session_id or ""),
                question_advanced=True,
                evaluator_status="complete",
            )
            yield {
                "type": "interview_progress",
                "content": json.dumps(advanced, ensure_ascii=False),
            }
        else:
            yield {
                "type": "thinking",
                "content": f"【{role_label}】Redis 进度未更新，请稍后再进入或继续作答。\n",
            }
    elif mq_err:
        yield {"type": "thinking", "content": f"【{role_label}】题完结 MQ 未发送：{mq_err}\n"}

    yield {
        "type": "interview_turn",
        "content": json.dumps(
            {
                "mode": "interview",
                "interviewer": turn_result.interviewer_output,
                "evaluator": turn_result.evaluator_output,
                "scorer": turn_result.scorer_output,
                "turn_result": turn_result.model_dump(),
            },
            ensure_ascii=False,
        ),
    }
    for piece in chunk_text(display):
        if bindings.cancel_event.is_set():
            break
        yield {"type": "answer", "content": piece}


def _question_text_from_redis(redis_ctx: Dict[str, Any], turn_ctx: Dict[str, Any]) -> str:
    """从 Redis ctx 的 current_question 或 questions[] 取当前题干正文。"""
    current = redis_ctx.get("current_question")
    if isinstance(current, dict):
        text = str(current.get("text") or "").strip()
        if text:
            return text
    seq = turn_ctx.get("seq_no")
    if seq is None:
        seq = redis_ctx.get("current_seq_no")
    qid = str(turn_ctx.get("question_id") or redis_ctx.get("current_question_id") or "").strip()
    questions = redis_ctx.get("questions")
    if isinstance(questions, list):
        for row in questions:
            if not isinstance(row, dict):
                continue
            if seq is not None and row.get("seq_no") == seq:
                return str(row.get("text") or "").strip()
            if qid and str(row.get("id") or "") == qid:
                return str(row.get("text") or "").strip()
    return ""
