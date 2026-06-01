"""
ROLE005 — 调用 server_job 内部 API 拉取面试上下文（无 PII 走 MQ 时的回调通道）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from app.session.role.role005.config import server_job_base_url, server_job_service_token
from app.session.role.role005.domain.models import ContextBundle
from app.session.role.role005.infra.schema_gate import validate_context_bundle

log = logging.getLogger(__name__)


def _headers() -> Dict[str, str]:
    token = server_job_service_token()
    h = {"Accept": "application/json"}
    if token:
        h["X-Service-Token"] = token
    return h


def fetch_context_bundle(interview_session_id: str) -> Optional[ContextBundle]:
    """
    GET /internal/interview/sessions/{id}/context-bundle

    server_job 未就绪或网络失败时返回 None，由调用方降级为 dev 构造上下文。
    """
    sid = (interview_session_id or "").strip()
    if not sid:
        return None
    url = f"{server_job_base_url()}/internal/interview/sessions/{sid}/context-bundle"
    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
        if resp.status_code == 404:
            log.warning("context-bundle 不存在: %s", sid)
            return None
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("拉取 context-bundle 失败 session=%s: %s", sid, exc)
        return None

    bundle, err = validate_context_bundle(data)
    if err:
        log.warning("context-bundle Schema 无效: %s", err)
        return None
    return bundle


def post_apply_turn_result(interview_session_id: str, body: Dict[str, Any]) -> bool:
    """大 payload 异步回填（可选）；P0 同步 /turn 可不调用。"""
    sid = (interview_session_id or "").strip()
    if not sid:
        return False
    url = f"{server_job_base_url()}/internal/interview/sessions/{sid}/apply-turn-result"
    try:
        resp = requests.post(url, json=body, headers=_headers(), timeout=60)
        resp.raise_for_status()
        return True
    except Exception as exc:
        log.warning("apply-turn-result 失败: %s", exc)
        return False
