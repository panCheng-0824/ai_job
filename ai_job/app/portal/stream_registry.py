"""流式生成取消句柄注册表（按 session_id）。"""

import threading
from typing import Any, Dict


_active_stream_cancellers: Dict[str, Any] = {}
_active_stream_lock = threading.Lock()


def register_stream_canceller(session_id: str, cancel_fn: Any) -> None:
    with _active_stream_lock:
        _active_stream_cancellers[session_id] = cancel_fn


def pop_stream_canceller(session_id: str) -> Any:
    with _active_stream_lock:
        return _active_stream_cancellers.pop(session_id, None)


def clear_stream_canceller_if_same(session_id: str, cancel_fn: Any) -> None:
    with _active_stream_lock:
        current = _active_stream_cancellers.get(session_id)
        if current is cancel_fn:
            _active_stream_cancellers.pop(session_id, None)


def safe_cancel(cancel_fn: Any) -> None:
    if not callable(cancel_fn):
        return
    try:
        cancel_fn()
    except Exception:
        pass
