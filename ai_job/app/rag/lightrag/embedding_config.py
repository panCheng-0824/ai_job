"""LightRAG embedding 参数解析模块。"""

from __future__ import annotations

import logging
import os
from typing import Any

from model_cfg import ModelEntry

log = logging.getLogger(__name__)


def _infer_dim_from_model_name(model_name: str) -> int:
    """根据常见模型名称推断 embedding 维度。"""
    name = (model_name or "").strip().lower()
    if not name:
        return -1
    # Qwen3-Embedding-0.6B 系列通常输出 1024 维
    if "qwen3-embedding-0.6b" in name:
        return 1024
    # OpenAI text-embedding-3-small 默认 1536
    if "text-embedding-3-small" in name:
        return 1536
    return -1


def resolve_embedding_params(chat_entry: ModelEntry, embedding_entry: ModelEntry | None) -> dict[str, Any]:
    """按优先级解析 embedding 相关参数。"""
    embedding_model = os.getenv("LIGHTRAG_EMBED_MODEL", "").strip()
    embedding_api = os.getenv("LIGHTRAG_EMBED_API", "").strip()
    embedding_key = os.getenv("LIGHTRAG_EMBED_KEY", "").strip()

    if not embedding_model and embedding_entry is not None:
        embedding_model = str(embedding_entry.get("model_name", "")).strip()
    if not embedding_api and embedding_entry is not None:
        embedding_api = str(embedding_entry.get("model_api", "")).strip()
    if not embedding_key and embedding_entry is not None:
        embedding_key = str(embedding_entry.get("model_key", "")).strip()

    if not embedding_model:
        embedding_model = str(chat_entry.get("model_name", "")).strip()
    if not embedding_api:
        embedding_api = str(chat_entry.get("model_api", "")).strip()
    if not embedding_key:
        embedding_key = str(chat_entry.get("model_key", "")).strip()
    if not embedding_model:
        embedding_model = "text-embedding-3-small"

    configured_dim = int(os.getenv("LIGHTRAG_EMBED_DIM", "1536"))
    inferred_dim = _infer_dim_from_model_name(embedding_model)
    strict_dim = os.getenv("LIGHTRAG_EMBED_DIM_STRICT", "0").strip().lower() in {"1", "true", "yes", "on"}
    embedding_dim = configured_dim
    if inferred_dim > 0 and not strict_dim:
        if configured_dim != inferred_dim:
            log.warning(
                "LightRAG Embedding 维度按模型自动纠偏, model=%s, configured_dim=%s, inferred_dim=%s, strict=%s",
                embedding_model,
                configured_dim,
                inferred_dim,
                strict_dim,
            )
        embedding_dim = inferred_dim
    max_token_size = int(os.getenv("LIGHTRAG_EMBED_MAX_TOKENS", "8192"))
    return {
        "model": embedding_model,
        "api": embedding_api,
        "key": embedding_key,
        "dim": embedding_dim,
        "max_tokens": max_token_size,
    }
