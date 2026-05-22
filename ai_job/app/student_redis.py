"""从 Redis 读取 server_job 登录时写入的学生画像（与 Java 共用同一实例与键前缀）。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_redis_client = None


def _build_redis():
    import redis

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD") or None
    db = int(os.getenv("REDIS_DATABASE", os.getenv("REDIS_DB", "0")))
    return redis.Redis(
        host=host,
        port=port,
        password=password,
        db=db,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=5,
    )


def student_profile_key_prefix() -> str:
    return os.getenv("STUDENT_PROFILE_REDIS_PREFIX", "student:profile:")


def get_student_profile_json(student_id: str) -> Optional[str]:
    sid = (student_id or "").strip()
    if not sid:
        return None
    global _redis_client
    try:
        if _redis_client is None:
            _redis_client = _build_redis()
        key = student_profile_key_prefix() + sid
        return _redis_client.get(key)
    except Exception as ex:
        logger.warning("读取 Redis 学生画像失败 student_id=%s: %s", sid, ex)
        return None


def get_student_profile(student_id: str) -> Optional[Dict[str, Any]]:
    raw = get_student_profile_json(student_id)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def format_student_profile_prompt_extra(student_id: str) -> str:
    """将 Redis 学生档案格式化为可拼入 system_prompt_extra 的文本块。"""
    sid = str(student_id or "").strip()
    if not sid:
        return ""
    try:
        prof = get_student_profile(sid)
        if not prof:
            return ""
        b1 = prof.get("学生基本信息")
        b2 = prof.get("奖励信息")
        if b1 or b2:
            return f"\n【档案摘要】学生基本信息：{b1}；奖学金/称号信息：{b2}\n"
    except Exception:
        pass
    return ""
