"""聊天会话 JSON 持久化。"""

import json
from typing import Any, Dict, List, Tuple

from app.portal.paths import SESSION_FILE


def ensure_session_file() -> None:
    if not SESSION_FILE.exists():
        with SESSION_FILE.open("w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_sessions() -> List[Dict[str, Any]]:
    ensure_session_file()
    with SESSION_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_sessions(sessions: List[Dict[str, Any]]) -> None:
    with SESSION_FILE.open("w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def find_session(
    sessions: List[Dict[str, Any]], session_id: str
) -> Tuple[int, Dict[str, Any] | None]:
    for idx, session in enumerate(sessions):
        if session.get("session_id") == session_id:
            return idx, session
    return -1, None
