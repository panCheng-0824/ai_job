"""
ROLE005 — SSE：未传入 turn JSON 时的操作引导（不调用 LLM）。
"""

from __future__ import annotations

import json
import uuid
from threading import Event
from typing import Dict, Iterator

from app.session.role.role_util.stream_common import chunk_text


def iter_chat_guide_tokens(*, cancel_event: Event) -> Iterator[Dict[str, str]]:
    """
    返回引导 JSON，说明如何通过 message_context 发起正式答题。

    避免用户误以为直连聊天即为完整面试流程。
    """
    guide = {
        "action": "guide",
        "message": (
            "模拟面试官已就绪。请在 message_context 传入 JSON 开始答题，"
            "或发送包含「规划/大纲」的消息生成面试大纲。"
        ),
        "example_turn": {
            "interview_session_id": "由 server_job 分配",
            "turn_id": str(uuid.uuid4()),
            "action": "start",
            "payload": {},
        },
    }
    text = json.dumps(guide, ensure_ascii=False, indent=2)
    for piece in chunk_text(text):
        if cancel_event.is_set():
            break
        yield {"type": "answer", "content": piece}
