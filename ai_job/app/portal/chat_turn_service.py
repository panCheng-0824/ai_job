"""会话内同步聊天、无状态 internal 完成调用等业务编排。"""

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.skills.adversarial_harness import run_adversarial_harness
from app.session.chat_service import run_chat_service
from app.session.chat_stream_pipeline import resolve_adversarial_max_rounds_from_user_model
from app.student_redis import format_student_profile_prompt_extra

from app.portal import data_catalog
from app.portal.errors import PortalError
from app.portal.schemas import ChatMessageRequest, InternalChatPayload


def _run_answer_sync(
    user_model: Dict[str, Any],
    usercode: str,
    text: str,
    history_turns: List[Dict[str, Any]],
    use_role_pipeline: bool,
    use_adversarial_harness: bool,
    adversarial_desc: str,
    profile_extra: str,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    harness_result: Dict[str, Any] | None = None
    answer = ""
    if use_adversarial_harness:
        try:
            harness_result = run_adversarial_harness(
                role_ref=usercode,
                adversary_desc=adversarial_desc,
                question=text,
                max_rounds=resolve_adversarial_max_rounds_from_user_model(user_model),
            )
            answer = str(harness_result.get("final_answer", "")).strip()
        except Exception as exc:
            raise PortalError(f"深度思考失败: {exc}", 502) from exc
    else:
        try:
            service_result = run_chat_service(
                usercode=usercode,
                message=text,
                history=history_turns,
                verbose=False,
                temperature=0.0,
                use_role_pipeline=use_role_pipeline,
                system_prompt_extra=profile_extra or None,
            )
        except RuntimeError as exc:
            raise PortalError(str(exc), 502) from exc
        answer = service_result["answer"]
    return answer, harness_result


def chat_turn_in_persisted_session(
    session_id: str, payload: ChatMessageRequest
) -> Dict[str, Any]:
    text = payload.message.strip()
    if not text:
        raise PortalError("message 不能为空", 400)

    from app.portal import session_store

    sessions = session_store.load_sessions()
    idx, session = session_store.find_session(sessions, session_id)
    if not session:
        raise PortalError("会话不存在，请先初始化会话", 404)

    usercode = str(session.get("usercode", "")).strip()
    user_model = data_catalog.user_models_index.get(usercode)
    if not user_model:
        raise PortalError("会话对应的 user_model 不存在", 404)

    history_turns = session.get("history", [])
    profile_extra = format_student_profile_prompt_extra(str(session.get("student_id", "")))

    answer, harness_result = _run_answer_sync(
        user_model,
        usercode=usercode,
        text=text,
        history_turns=history_turns,
        use_role_pipeline=payload.use_role_pipeline,
        use_adversarial_harness=payload.use_adversarial_harness,
        adversarial_desc=payload.adversarial_desc,
        profile_extra=profile_extra,
    )

    now = datetime.utcnow().isoformat() + "Z"
    history_turns.append({"role": "user", "content": text, "ts": now})
    history_turns.append({"role": "assistant", "content": answer, "ts": now})
    session["history"] = history_turns
    sessions[idx] = session
    session_store.save_sessions(sessions)

    return {
        "session_id": session_id,
        "usercode": usercode,
        "model_level": session.get("model_level", ""),
        "use_role_pipeline": payload.use_role_pipeline,
        "use_adversarial_harness": payload.use_adversarial_harness,
        "adversarial_review": (harness_result or {}).get("final_review", ""),
        "adversarial_rounds_used": (harness_result or {}).get("rounds_used", 0),
        "answer": answer,
        "history": history_turns,
    }


def internal_chat_complete_result(payload: InternalChatPayload) -> Dict[str, Any]:
    sid = payload.session_id.strip()
    if not sid:
        raise PortalError("session_id 不能为空", 400)
    text = payload.message.strip()
    if not text:
        raise PortalError("message 不能为空", 400)

    user_model = data_catalog.get_user_model_or_raise(payload.usercode)
    usercode = str(user_model.get("usercode", "")).strip()
    history_turns = copy.deepcopy(payload.history)
    profile_extra = format_student_profile_prompt_extra(payload.student_id)

    answer, harness_result = _run_answer_sync(
        user_model,
        usercode=usercode,
        text=text,
        history_turns=history_turns,
        use_role_pipeline=payload.use_role_pipeline,
        use_adversarial_harness=payload.use_adversarial_harness,
        adversarial_desc=payload.adversarial_desc,
        profile_extra=profile_extra,
    )

    now = datetime.utcnow().isoformat() + "Z"
    history_turns.append({"role": "user", "content": text, "ts": now})
    history_turns.append({"role": "assistant", "content": answer, "ts": now})

    return {
        "session_id": sid,
        "usercode": usercode,
        "model_level": user_model.get("model_level", ""),
        "use_role_pipeline": payload.use_role_pipeline,
        "use_adversarial_harness": payload.use_adversarial_harness,
        "adversarial_review": (harness_result or {}).get("final_review", ""),
        "adversarial_rounds_used": (harness_result or {}).get("rounds_used", 0),
        "answer": answer,
        "history": history_turns,
    }
