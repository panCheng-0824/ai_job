"""LightRAG 写入前文档清洗（LLM）参数解析，优先级对齐 embedding 配置。"""

from __future__ import annotations

import os
from typing import Any

from model_cfg import ModelEntry


def doc_clean_enabled() -> bool:
    return os.getenv("LIGHTRAG_DOC_CLEAN_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def doc_clean_on_error_fallback() -> bool:
    """LLM 清洗失败时是否回退为 strip 后的原文。"""
    return os.getenv("LIGHTRAG_DOC_CLEAN_ON_ERROR", "fallback").strip().lower() in {
        "fallback",
        "1",
        "true",
        "yes",
        "on",
    }


def resolve_doc_clean_params(chat_entry: ModelEntry, clean_entry: ModelEntry | None) -> dict[str, Any]:
    """按优先级解析文档清洗模型：env 直配 > modelCfg 选中项 > 回退 chat。"""
    model = os.getenv("LIGHTRAG_DOC_CLEAN_MODEL", "").strip()
    api = os.getenv("LIGHTRAG_DOC_CLEAN_API", "").strip()
    key = os.getenv("LIGHTRAG_DOC_CLEAN_KEY", "").strip()

    if not model and clean_entry is not None:
        model = str(clean_entry.get("model_name", "")).strip()
    if not api and clean_entry is not None:
        api = str(clean_entry.get("model_api", "")).strip()
    if not key and clean_entry is not None:
        key = str(clean_entry.get("model_key", "")).strip()

    if not model:
        model = str(chat_entry.get("model_name", "")).strip()
    if not api:
        api = str(chat_entry.get("model_api", "")).strip()
    if not key:
        key = str(chat_entry.get("model_key", "")).strip()

    temperature = float(os.getenv("LIGHTRAG_DOC_CLEAN_TEMPERATURE", "0") or "0")
    max_chars = int(os.getenv("LIGHTRAG_DOC_CLEAN_MAX_CHARS", "0") or "0")
    system_prompt = (os.getenv("LIGHTRAG_DOC_CLEAN_SYSTEM_PROMPT", "").strip() or _default_system_prompt())

    return {
        "model": model,
        "api": api,
        "key": key,
        "temperature": temperature,
        "max_chars": max_chars,
        "system_prompt": system_prompt,
    }


def _default_system_prompt() -> str:
    return (
        "你是文档预处理助手。用户将提供待入库的 Markdown 或纯文本。"
        "请在不编造事实的前提下完成清洗：修正明显乱码与多余空白，统一换行，保留原有结构与中文含义；"
        "不要添加原文没有的信息；直接输出清洗后的正文，不要输出解释或前后缀。"
    )
