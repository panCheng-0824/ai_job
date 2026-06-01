"""
行业分类 Redis 读取 — 与 server_job ``IndustryCategoryRedisKeys`` 键规范一致。

- ``top_category``：一级行业桶
- ``{一级 category_id}``：该一级下二级行业桶
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from app.session.role.role005.config import server_job_base_url, server_job_service_token

log = logging.getLogger(__name__)

TOP_CATEGORY_KEY = os.getenv("INTERVIEW_INDUSTRY_TOP_KEY", "top_category")

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


def _headers() -> Dict[str, str]:
    token = server_job_service_token()
    h = {"Accept": "application/json"}
    if token:
        h["X-Service-Token"] = token
    return h


def _parse_bucket(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {"items": [], "count": 0}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return data
    except json.JSONDecodeError:
        log.warning("行业 Redis 桶 JSON 无效")
    return {"items": [], "count": 0}


def _read_redis_bucket(key: str) -> Optional[Dict[str, Any]]:
    global _redis_client
    try:
        if _redis_client is None:
            _redis_client = _build_redis()
        raw = _redis_client.get(key)
        if not raw:
            return None
        return _parse_bucket(raw)
    except Exception as exc:
        log.warning("读取行业 Redis 失败 key=%s: %s", key, exc)
        return None


def _fetch_http_bucket(path: str) -> Dict[str, Any]:
    url = f"{server_job_base_url()}{path}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return data
    except Exception as exc:
        log.warning("HTTP 拉取行业桶失败 path=%s: %s", path, exc)
    return {"items": [], "count": 0}


def fetch_top_categories() -> List[Dict[str, Any]]:
    """获取一级行业候选（Redis 优先，失败走 server_job 内部 API）。"""
    bucket = _read_redis_bucket(TOP_CATEGORY_KEY)
    if bucket is None:
        bucket = _fetch_http_bucket("/internal/interview/industry/cache/top")
    items = bucket.get("items") or []
    return [x for x in items if isinstance(x, dict)]


def fetch_level2_categories(level1_category_id: str) -> List[Dict[str, Any]]:
    """获取某一级下的二级行业候选。"""
    pid = (level1_category_id or "").strip()
    if not pid:
        return []
    bucket = _read_redis_bucket(pid)
    if bucket is None:
        bucket = _fetch_http_bucket(f"/internal/interview/industry/cache/l2/{pid}")
    items = bucket.get("items") or []
    return [x for x in items if isinstance(x, dict)]
