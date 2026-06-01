"""
ROLE005 运行时配置。

环境变量
--------
- ``ROLE005_INTERVIEW_ENABLED``：总开关，0 关闭 SSE/API
- ``ROLE005_LLM_TIMEOUT_S``：单次 LLM 超时（默认 180s）
- ``ROLE005_LLM_RESPONSE_FORMAT``：结构化输出，``json_object``（默认）/ ``none`` 关闭
- ``SERVER_JOB_BASE_URL``：拉取 context-bundle
- ``SERVER_JOB_SERVICE_TOKEN``：服务间鉴权
- ``ROLE``：``ai_job_a``（API）或 ``ai_job_b``（Worker）

RocketMQ 连接项见 ``app/mq/settings.py``（``ROCKETMQ_PROXY_GRPC_ENDPOINT`` / ``ROCKETMQ_NAMESERVER`` 等）。
"""

from __future__ import annotations

import os
from typing import Any, Dict

from pipeline_llm import resolve_float_setting


def interview_enabled() -> bool:
    """功能开关：关闭时流式入口返回友好提示。"""
    return os.getenv("ROLE005_INTERVIEW_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def resolve_role005_llm_response_format() -> Dict[str, Any] | None:
    """
    Planner 等 JSON Agent 使用的 ``response_format``。

    - ``json_object`` / ``json``（默认）：``{"type": "json_object"}``
    - ``none`` / ``off``：不传，仅靠 Prompt + ``parse_json_object`` 剥离围栏
    """
    mode = (
        os.getenv("ROLE005_LLM_RESPONSE_FORMAT", "json_object") or "json_object"
    ).strip().lower()
    if mode in ("none", "off", "disabled", "0", "false"):
        return None
    if mode in ("json_object", "json"):
        return {"type": "json_object"}
    return {"type": "json_object"}


def resolve_role005_llm_timeout_seconds(merged_user: Dict[str, Any] | None = None) -> float:
    """
    模拟面试官 LLM 单次超时（秒）。

    多 Agent 串联时单次可能较慢，默认 180s。
    """
    if isinstance(merged_user, dict):
        opts = merged_user.get("stream_options")
        if isinstance(opts, dict) and opts.get("role005_llm_timeout_s") is not None:
            try:
                v = float(opts["role005_llm_timeout_s"])
                if v > 0:
                    return v
            except (TypeError, ValueError):
                pass
    return resolve_float_setting(
        env_key="ROLE005_LLM_TIMEOUT_S",
        config_key="role005_llm_timeout_s",
        default=180.0,
        min_value=60.0,
    )


def server_job_base_url() -> str:
    """server_job 根地址，供拉取 context-bundle。"""
    return os.getenv("SERVER_JOB_BASE_URL", "http://127.0.0.1:8080").rstrip("/")


def server_job_service_token() -> str:
    """服务间鉴权 Token（与 server_job 约定 X-Service-Token）。"""
    return os.getenv("SERVER_JOB_SERVICE_TOKEN", "").strip()


def ai_job_role() -> str:
    """进程角色：ai_job_a（API）或 ai_job_b（Worker）。"""
    return os.getenv("ROLE", "ai_job_a").strip() or "ai_job_a"


def plan_bank_mq_enabled() -> bool:
    """规划图完成后是否向 ``interview_ai_result`` 投递大纲题库消息。"""
    return os.getenv("ROLE005_PLAN_BANK_MQ_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
