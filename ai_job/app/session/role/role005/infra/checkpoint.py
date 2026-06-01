"""
ROLE005 — LangGraph Checkpoint 占位（Redis 实现待接）。

业务真相在 server_job；Checkpoint 仅用于 ai_job 断线恢复加速。
"""

from __future__ import annotations

import uuid
from typing import Optional


def save_checkpoint_hint(session_id: str, graph_state: dict) -> str:
    """
    保存图状态快照 ID（P0 仅占位，返回随机 ID）。

    后续接入 Redis + LangGraph Checkpointer。
    """
    _ = graph_state
    return f"ckpt_{session_id}_{uuid.uuid4().hex[:12]}"


def load_checkpoint_hint(checkpoint_id: str) -> Optional[dict]:
    """按 checkpoint_id 恢复图状态；未实现时返回 None。"""
    _ = checkpoint_id
    return None
