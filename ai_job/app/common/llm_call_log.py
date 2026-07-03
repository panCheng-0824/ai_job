"""大模型调用日志：统一记录业务场景与所用模型。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from model_cfg import ModelEntry

log = logging.getLogger(__name__)


def _fmt_response_format(response_format: Optional[Dict[str, Any]]) -> str:
    if not response_format:
        return "none"
    rf_type = response_format.get("type")
    if rf_type == "json_schema":
        strict = (response_format.get("json_schema") or {}).get("strict")
        return f"json_schema(strict={strict})"
    return str(rf_type or "unknown")


def log_llm_call(
    scenario: str,
    *,
    model_name: str,
    model_api: str = "",
    model_level: str = "",
    response_format: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> None:
    """
    记录一次大模型调用前的场景与模型信息。

    extra 可传 temperature、max_tokens 等，会拼入日志便于排查。
    """
    parts = [
        f"场景={scenario}",
        f"model={model_name}",
    ]
    if model_level:
        parts.append(f"level={model_level}")
    if model_api:
        parts.append(f"api={model_api}")
    if response_format is not None:
        parts.append(f"response_format={_fmt_response_format(response_format)}")
    for key, value in extra.items():
        if value is not None and value != "":
            parts.append(f"{key}={value}")
    log.info("LLM调用 %s", ", ".join(parts))


def log_llm_call_from_entry(
    scenario: str,
    entry: ModelEntry,
    *,
    response_format: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> None:
    """基于 modelCfg 条目记录 LLM 调用。"""
    log_llm_call(
        scenario,
        model_name=str(entry.get("model_name") or ""),
        model_api=str(entry.get("model_api") or ""),
        model_level=str(entry.get("model_level") or ""),
        response_format=response_format,
        **extra,
    )


def log_llm_call_from_langchain(
    scenario: str,
    llm: Any,
    *,
    model_level: str = "",
    response_format: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> None:
    """基于 LangChain ChatModel 实例记录 LLM 调用。"""
    model_name = (
        getattr(llm, "model_name", None)
        or getattr(llm, "model", None)
        or "unknown"
    )
    model_api = (
        getattr(llm, "openai_api_base", None)
        or getattr(llm, "base_url", None)
        or ""
    )
    log_llm_call(
        scenario,
        model_name=str(model_name),
        model_api=str(model_api),
        model_level=model_level,
        response_format=response_format,
        **extra,
    )
