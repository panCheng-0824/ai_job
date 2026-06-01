"""
ROLE005 — 整场面试 Redis ctx 读写（``interview:ctx:{student_id}:{record_id}``）。

读：ai_job 答题流程入口。
写：题完结 MQ 发送后的乐观推进（与 server MQ 消费幂等对齐，避免消费延迟重复答题）。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.session.role.role005.infra.interview_qsess_redis import redis_client

log = logging.getLogger(__name__)

# 与 server InterviewContextRedisSupport CTX_TTL 24h 对齐
_CTX_TTL_SECONDS = int(os.getenv("ROLE005_CTX_TTL_SECONDS", "86400"))


def ctx_redis_key(student_id: str, record_id: str) -> str:
    """与 server_job ``InterviewRedisKeys.ctx`` 对齐。"""
    sid = (student_id or "").strip()
    rid = (record_id or "").strip()
    return f"interview:ctx:{sid}:{rid}"


def load_interview_ctx(
    *,
    student_id: str = "",
    record_id: str = "",
    ctx_key: str = "",
) -> Optional[Dict[str, Any]]:
    """
    读取整场面试 Redis ctx。

    参数
    ----
    ctx_key :
        web 传入的 key，优先使用。
    student_id / record_id :
        未传 ctx_key 时按规范拼接。
    """
    key = (ctx_key or "").strip() or ctx_redis_key(student_id, record_id)
    if not key or key.endswith(":"):
        return None
    try:
        raw = redis_client().get(key)
        if not raw:
            log.warning("interview ctx 不存在 key=%s", key)
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return data
    except Exception as exc:
        log.warning("读取 interview ctx 失败 key=%s: %s", key, exc)
        return None


def save_interview_ctx(
    ctx: Dict[str, Any],
    *,
    student_id: str = "",
    record_id: str = "",
    ctx_key: str = "",
    ttl_seconds: int | None = None,
) -> bool:
    """
    写回整场 ctx（乐观推进进度用）。

    server MQ 消费后会再次覆盖；若该题已 completed 则双方幂等。
    """
    key = (ctx_key or "").strip() or ctx_redis_key(student_id, record_id)
    if not key or key.endswith(":"):
        return False
    ttl = ttl_seconds if ttl_seconds is not None else _CTX_TTL_SECONDS
    try:
        payload = dict(ctx)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        redis_client().setex(key, ttl, json.dumps(payload, ensure_ascii=False))
        log.info("interview ctx 已乐观写回 key=%s seq=%s", key, payload.get("current_seq_no"))
        return True
    except Exception as exc:
        log.warning("写入 interview ctx 失败 key=%s: %s", key, exc)
        return False


def optimistic_advance_after_question_complete(
    *,
    student_id: str,
    record_id: str,
    completed_seq_no: int,
    ctx_key: str = "",
) -> Optional[Dict[str, Any]]:
    """
    MQ 发送成功后：重新读 ctx → 标记本题 completed → 指针指下一题 → 写回 Redis。

    返回写回后的 ctx；失败返回 None。
    """
    from app.session.role.role005.stream_handlers.interview_ctx_resume import (
        patch_ctx_after_question_completed,
    )

    fresh = load_interview_ctx(
        student_id=student_id,
        record_id=record_id,
        ctx_key=ctx_key,
    )
    if not fresh:
        return None
    patched = patch_ctx_after_question_completed(fresh, completed_seq_no)
    if not save_interview_ctx(
        patched,
        student_id=student_id,
        record_id=record_id,
        ctx_key=ctx_key,
    ):
        return None
    return patched
