"""
ROLE005 — LangGraph Checkpointer（Redis ShallowRedisSaver）。

业务真相在 server_job；Checkpoint 仅用于 ai_job 断线恢复加速。
依赖 Redis 8+ 或 Redis Stack（RedisJSON + RediSearch）。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import quote

log = logging.getLogger(__name__)

_CHECKPOINTER: Any = None
_CHECKPOINTER_TRIED = False
_CHECKPOINTER_DISABLED = False


def _checkpoint_enabled() -> bool:
    return os.getenv("ROLE005_CHECKPOINT_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _redis_db() -> int:
    raw = os.getenv("REDIS_DB")
    if raw is None or raw == "":
        raw = os.getenv("REDIS_DATABASE", "0")
    return int(raw)


def _redis_uri() -> str:
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = _redis_db()
    password = (os.getenv("REDIS_PASSWORD") or "").strip()
    if password:
        return f"redis://:{quote(password, safe='')}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


def _checkpoint_ttl_config() -> Dict[str, Any]:
    ttl_minutes = int(os.getenv("ROLE005_CHECKPOINT_TTL_MINUTES", "1440"))
    refresh = os.getenv("ROLE005_CHECKPOINT_REFRESH_ON_READ", "1").strip().lower()
    return {
        "default_ttl": ttl_minutes,
        "refresh_on_read": refresh not in ("0", "false", "no"),
    }


def get_interview_checkpointer() -> Optional[Any]:
    """
    返回进程级单例 ShallowRedisSaver；初始化失败或未启用时返回 None。

    Shallow 实现每 thread 只保留最新 checkpoint，适合 ephemeral 运行态。
    """
    global _CHECKPOINTER, _CHECKPOINTER_TRIED, _CHECKPOINTER_DISABLED

    if not _checkpoint_enabled():
        return None
    if _CHECKPOINTER_TRIED:
        return None if _CHECKPOINTER_DISABLED else _CHECKPOINTER

    _CHECKPOINTER_TRIED = True
    try:
        from langgraph.checkpoint.redis.shallow import ShallowRedisSaver

        saver = ShallowRedisSaver(
            redis_url=_redis_uri(),
            ttl=_checkpoint_ttl_config(),
        )
        saver.setup()
        _CHECKPOINTER = saver
        log.info("ROLE005 LangGraph checkpointer 已就绪（ShallowRedisSaver）")
        return _CHECKPOINTER
    except Exception as exc:
        _CHECKPOINTER_DISABLED = True
        log.warning(
            "ROLE005 checkpointer 初始化失败，答题图将不挂 checkpointer: %s",
            exc,
        )
        return None


def interview_turn_thread_config(
    interview_session_id: str,
    *,
    recursion_limit: int = 24,
) -> Dict[str, Any]:
    """LangGraph invoke 用的 thread 配置；thread_id 对齐 interview_session_id。"""
    thread_id = (interview_session_id or "").strip()
    if not thread_id:
        raise ValueError("interview_session_id 不能为空")
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }


def extract_checkpoint_id(snapshot: Any) -> str:
    """从 compiled.get_state(config) 返回的 StateSnapshot 提取 checkpoint_id。"""
    try:
        configurable = snapshot.config.get("configurable", {})
        return str(configurable.get("checkpoint_id") or "")
    except Exception:
        return ""


def load_checkpoint_tuple(interview_session_id: str) -> Optional[Any]:
    """按 thread_id 读取最新 checkpoint tuple；无 checkpointer 或无快照时返回 None。"""
    checkpointer = get_interview_checkpointer()
    if checkpointer is None:
        return None
    thread_id = (interview_session_id or "").strip()
    if not thread_id:
        return None
    try:
        return checkpointer.get_tuple({"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        log.warning("读取 checkpoint 失败 thread_id=%s: %s", thread_id, exc)
        return None
