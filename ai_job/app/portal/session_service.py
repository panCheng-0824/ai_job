"""聊天会话 CRUD 与初始化（文件持久化）。"""

from datetime import datetime
from typing import Any, Dict, List

from app.portal import data_catalog, session_store
from app.portal.errors import PortalError
from app.session.role.role005.greeting import seed_role005_session_greeting


def get_session_or_raise(session_id: str) -> Dict[str, Any]:
    sessions = session_store.load_sessions()
    _, session = session_store.find_session(sessions, session_id)
    if session:
        return session
    raise PortalError("会话不存在", 404)


def list_sessions_for_student(student_id: str) -> List[Dict[str, Any]]:
    sid = (student_id or "").strip()
    if not sid:
        raise PortalError("student_id 不能为空", 400)
    sessions = session_store.load_sessions()
    data = [s for s in sessions if s.get("student_id") == sid]
    data.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return data


def delete_session(session_id: str) -> Dict[str, Any]:
    sessions = session_store.load_sessions()
    idx, session = session_store.find_session(sessions, session_id)
    if not session:
        raise PortalError("会话不存在", 404)
    sessions.pop(idx)
    session_store.save_sessions(sessions)
    return {"deleted": True, "session_id": session_id}


def init_session(
    session_id: str,
    student_id: str,
    usercode: str,
) -> Dict[str, Any]:
    sid = session_id.strip()
    stu = student_id.strip()
    uc = usercode.strip()

    if not sid:
        raise PortalError("session_id 不能为空", 400)
    if not stu:
        raise PortalError("student_id 不能为空", 400)
    if not uc:
        raise PortalError("usercode 不能为空", 400)

    data_catalog.ensure_student_exists(stu)
    data_catalog.ensure_user_model_exists(uc)

    sessions = session_store.load_sessions()
    _, existing = session_store.find_session(sessions, sid)
    if existing:
        if seed_role005_session_greeting(existing):
            session_store.save_sessions(sessions)
        return {
            "created": False,
            "session": existing,
            "message": "已存在会话，返回历史记录",
        }

    created_at = datetime.utcnow().isoformat() + "Z"
    new_session = data_catalog.build_new_chat_session(sid, stu, uc, created_at)
    seed_role005_session_greeting(new_session)
    sessions.append(new_session)
    session_store.save_sessions(sessions)
    return {
        "created": True,
        "session": new_session,
        "message": "会话不存在，已创建新会话",
    }


def get_history_bundle(session_id: str) -> Dict[str, Any]:
    sessions = session_store.load_sessions()
    _, session = session_store.find_session(sessions, session_id)
    if not session:
        raise PortalError("会话不存在", 404)
    return {"session_id": session_id, "history": session.get("history", [])}


def load_session_pair_or_raise(session_id: str):
    """返回 (sessions, idx, session) 供流式回调持久化。"""
    sessions = session_store.load_sessions()
    idx, session = session_store.find_session(sessions, session_id)
    if not session:
        raise PortalError("会话不存在，请先初始化会话", 404)
    return sessions, idx, session
