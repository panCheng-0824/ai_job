"""
ROLE005 — 单题多轮 Redis 会话（qsess）读写。

key 规范与 server_job ``InterviewRedisKeys.questionSession`` 一致，TTL 默认 2 小时。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

_redis_client = None
_QSESS_TTL_SECONDS = int(os.getenv("ROLE005_QSESS_TTL_SECONDS", "7200"))


def _build_redis():
    import redis

    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD") or None
    return redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)


def redis_client():
    """供 ctx / qsess 共用的 Redis 连接。"""
    global _redis_client
    if _redis_client is None:
        _redis_client = _build_redis()
    return _redis_client


def _client():
    return redis_client()


def load_qsess(key: str) -> Optional[Dict[str, Any]]:
    """读取单题 qsess；不存在返回 None。"""
    k = (key or "").strip()
    if not k:
        return None
    try:
        raw = _client().get(k)
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        log.warning("读取 qsess 失败 key=%s: %s", k, exc)
        return None


def save_qsess(key: str, data: Dict[str, Any], *, ttl_seconds: int | None = None) -> bool:
    """写入单题 qsess。"""
    k = (key or "").strip()
    if not k:
        return False
    ttl = ttl_seconds if ttl_seconds is not None else _QSESS_TTL_SECONDS
    try:
        _client().setex(k, ttl, json.dumps(data, ensure_ascii=False))
        return True
    except Exception as exc:
        log.warning("写入 qsess 失败 key=%s: %s", k, exc)
        return False


def delete_qsess(key: str) -> None:
    """题完结后删除 qsess。"""
    k = (key or "").strip()
    if not k:
        return
    try:
        _client().delete(k)
    except Exception as exc:
        log.warning("删除 qsess 失败 key=%s: %s", k, exc)


def append_qsess_turn(
    key: str,
    *,
    role: str,
    text: str,
    base: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """追加一轮对话到 qsess 并写回 Redis。"""
    data = dict(base or load_qsess(key) or {})
    turns = list(data.get("turns") or [])
    turns.append({"role": role, "text": (text or "").strip()})
    data["turns"] = turns
    save_qsess(key, data)
    return data
