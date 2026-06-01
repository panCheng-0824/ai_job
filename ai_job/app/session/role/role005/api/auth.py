"""
ROLE005 内部 API 鉴权 — 服务间 X-Service-Token。
"""

from __future__ import annotations

from fastapi import HTTPException

from app.session.role.role005.config import server_job_service_token


def verify_service_token(x_service_token: str | None) -> None:
    """
    校验调用方 Token。

    未配置 ``SERVER_JOB_SERVICE_TOKEN`` 时跳过（仅建议本地开发）。
    """
    expected = server_job_service_token()
    if not expected:
        return
    if (x_service_token or "").strip() != expected:
        raise HTTPException(status_code=401, detail="无效的服务间 Token")
