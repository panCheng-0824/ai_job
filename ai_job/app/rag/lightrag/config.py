"""LightRAG 配置定义与环境变量解析。"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LightRAGConfig:
    """LightRAG 运行时配置（含图存储、向量存储与检索参数）。"""

    model_level: str = "mid"
    working_dir: str = "./rag_storage"
    workspace: str = "ai_job"
    graph_storage: str = "Neo4JStorage"
    vector_storage: str = "MilvusVectorDBStorage"
    query_mode: str = "mix"
    top_k: int = 20


def resolve_lightrag_working_dir(cfg: LightRAGConfig) -> Path:
    """
    解析 LightRAG 实际使用的 working_dir 绝对路径。

    当 ``LIGHTRAG_WORKING_DIR`` 指向 ``rag_storage`` 而历史数据在
    ``rag_storage/<LIGHTRAG_WORKSPACE>/kv_store_doc_status.json`` 时，
    自动选用子目录，避免内存中的 doc_status 与磁盘上正在查看的 JSON 不一致，
    从而导致 ``adelete_by_doc_id`` 一直 ``not_found``、pending 清不掉。
    """
    base = Path(cfg.working_dir).expanduser().resolve()
    ws = (cfg.workspace or "").strip().strip("/\\")
    if ws:
        nested = base / ws
        if nested.is_dir() and (nested / "kv_store_doc_status.json").is_file():
            log.info("LightRAG working_dir 选用 workspace 子目录, path=%s", nested)
            return nested
    return base


def missing_milvus_env_vars() -> list[str]:
    """检查 Milvus 必要环境变量是否缺失。"""
    required = ("MILVUS_URI", "MILVUS_DB_NAME")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        log.warning("LightRAG 检测到 Milvus 必填环境变量缺失: %s", ", ".join(missing))
    else:
        log.info("LightRAG Milvus 必填环境变量检查通过")
    return missing


def resolve_vector_storage(raw_storage: str) -> str:
    """解析向量存储类型，必要时从 Milvus 自动降级到本地存储。"""
    storage = (raw_storage or "MilvusVectorDBStorage").strip() or "MilvusVectorDBStorage"
    log.info("LightRAG 向量存储解析开始, requested=%s", storage)
    if storage != "MilvusVectorDBStorage":
        log.info("LightRAG 向量存储使用非 Milvus 实现: %s", storage)
        return storage
    missing = missing_milvus_env_vars()
    if not missing:
        log.info("LightRAG 向量存储确认使用 Milvus")
        return storage
    fallback_enabled = os.getenv("LIGHTRAG_ALLOW_MILVUS_FALLBACK", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if fallback_enabled:
        log.warning("LightRAG 启用 Milvus 降级, fallback=NanoVectorDBStorage")
        return "NanoVectorDBStorage"
    raise ValueError(
        "Milvus 配置不完整，缺少环境变量: "
        f"{', '.join(missing)}。"
        "请设置后重启，或设置 LIGHTRAG_ALLOW_MILVUS_FALLBACK=1 允许自动降级。"
    )


def load_lightrag_config_from_env() -> LightRAGConfig:
    """从环境变量构建 LightRAG 配置。"""
    graph_storage = (os.getenv("LIGHTRAG_GRAPH_STORAGE", "Neo4JStorage").strip() or "Neo4JStorage")
    vector_storage = resolve_vector_storage(os.getenv("LIGHTRAG_VECTOR_STORAGE", "MilvusVectorDBStorage"))
    cfg = LightRAGConfig(
        model_level=os.getenv("LIGHTRAG_MODEL_LEVEL", "mid"),
        working_dir=os.getenv("LIGHTRAG_WORKING_DIR", "./rag_storage"),
        workspace=os.getenv("LIGHTRAG_WORKSPACE", "ai_job"),
        graph_storage=graph_storage,
        vector_storage=vector_storage,
        query_mode=os.getenv("LIGHTRAG_QUERY_MODE", "mix"),
        top_k=int(os.getenv("LIGHTRAG_TOP_K", "20")),
    )
    log.info("LightRAG 环境配置加载完成, config=%s", cfg)
    return cfg
