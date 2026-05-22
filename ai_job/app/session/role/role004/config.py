"""
ROLE004 运行时配置（超时等）。
"""

from __future__ import annotations

from typing import Any, Dict

from pipeline_llm import resolve_float_setting


def resolve_role004_llm_timeout_seconds(merged_user: Dict[str, Any] | None = None) -> float:
    """
    简历优化师 LLM 单次请求超时（秒）。

    整份简历 JSON 生成通常慢于普通对话，默认 120s。

    优先级：
    ``stream_options.role004_llm_timeout_s`` → 环境变量 ``ROLE004_LLM_TIMEOUT_S``
    → ``runtime_config.role004_llm_timeout_s`` → 默认 120。
    """
    if isinstance(merged_user, dict):
        opts = merged_user.get("stream_options")
        if isinstance(opts, dict) and opts.get("role004_llm_timeout_s") is not None:
            try:
                v = float(opts["role004_llm_timeout_s"])
                if v > 0:
                    return v
            except (TypeError, ValueError):
                pass
        raw = merged_user.get("role004_llm_timeout_s")
        if raw is not None:
            try:
                v = float(raw)
                if v > 0:
                    return v
            except (TypeError, ValueError):
                pass

    return resolve_float_setting(
        env_key="ROLE004_LLM_TIMEOUT_S",
        config_key="role004_llm_timeout_s",
        default=120.0,
        min_value=30.0,
    )
