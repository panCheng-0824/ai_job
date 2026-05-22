"""
================================================================================
Milvus Store（为 Day6/Day9 服务）：建表 / 写入 / 检索 的独立封装
================================================================================

为什么要抽出来？
--------------
Day6 原本把“业务流程（ingest/query）”和“数据库细节（Milvus schema/search）”混在一起。
当你想升级成 “向量 RAG + 知识图谱 RAG（Neo4j）” 时，最好把存储层拆分：

- `day6.py`：负责 **流程编排**（清洗→分块→嵌入→写入→查询→合并）
- `milvus_day6_store.py`：负责 **Milvus 的所有细节**

这样你以后把向量库从 Milvus 换成 FAISS/Chroma/PGVector，也只改这一层。
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, utility

# 复用 Day5 里的通用函数（连接、嵌入、建索引等）
from study01.day5 import (
    MilvusConfig,
    OllamaEmbedConfig,
    assert_vector_dim,
    connect_milvus,
    create_ollama_embedder,
    disconnect_milvus,
    embed_documents_texts,
    embed_query_text,
    ensure_vector_index_and_load,
)


# Day6 这套 RAG 表的字段名（与原 day6.py 保持一致）
PK_FIELD = "chunk_id"
VECTOR_FIELD = "embedding"
CONTENT_FIELD = "content"
SOURCE_FIELD = "source"


@dataclass(frozen=True)
class Day6MilvusConfig:
    """
    Day6 专用 Milvus 配置（尽量薄：只描述“怎么连”和“表叫什么”）。
    """

    host: str = os.environ.get("MILVUS_HOST", "127.0.0.1")
    port: int = int(os.environ.get("MILVUS_PORT", "19530"))
    alias: str = "default"
    collection_name: str = os.environ.get("MILVUS_COLLECTION_DAY6", "study01_day6_rag")
    vector_dim: int = int(os.environ.get("MILVUS_VECTOR_DIM", "768"))
    metric_type: str = os.environ.get("MILVUS_METRIC", "COSINE")


def to_day5_milvus_cfg(cfg: Day6MilvusConfig) -> MilvusConfig:
    """桥接到 Day5 的 MilvusConfig（Day5 里已有大量可复用通用函数）。"""
    return MilvusConfig(
        host=cfg.host,
        port=cfg.port,
        alias=cfg.alias,
        collection_name=cfg.collection_name,
        vector_dim=cfg.vector_dim,
        metric_type=cfg.metric_type,
    )


def build_schema(cfg: Day6MilvusConfig) -> CollectionSchema:
    """构建 Day6 的集合 Schema（字段顺序会影响 insert 的列顺序）。"""
    fields = [
        FieldSchema(
            name=PK_FIELD,
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=128,
        ),
        FieldSchema(name=VECTOR_FIELD, dtype=DataType.FLOAT_VECTOR, dim=cfg.vector_dim),
        FieldSchema(name=CONTENT_FIELD, dtype=DataType.VARCHAR, max_length=16384),
        FieldSchema(name=SOURCE_FIELD, dtype=DataType.VARCHAR, max_length=512),
    ]
    return CollectionSchema(fields=fields, description="Day6 RAG chunks", enable_dynamic_field=False)


def open_or_create_collection(cfg: Day6MilvusConfig) -> Collection:
    """在已 connect 的前提下：打开或创建集合。"""
    if utility.has_collection(cfg.collection_name, using=cfg.alias):
        return Collection(cfg.collection_name, using=cfg.alias)
    return Collection(name=cfg.collection_name, schema=build_schema(cfg), using=cfg.alias)


def ensure_collection_ready(cfg: Day6MilvusConfig) -> Collection:
    """
    查询前调用：确保已连接、集合存在、索引与 load 完成。
    """
    bridge = to_day5_milvus_cfg(cfg)
    connect_milvus(bridge)
    if not utility.has_collection(cfg.collection_name, using=cfg.alias):
        raise FileNotFoundError(f"集合不存在: {cfg.collection_name}，请先 ingest")
    coll = Collection(cfg.collection_name, using=cfg.alias)
    ensure_vector_index_and_load(coll, bridge)
    return coll


def drop_collection(cfg: Day6MilvusConfig) -> None:
    """学习阶段用：清空重来。"""
    if utility.has_collection(cfg.collection_name, using=cfg.alias):
        utility.drop_collection(cfg.collection_name, using=cfg.alias)


def insert_chunks(
    collection: Collection,
    *,
    chunk_ids: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    contents: Sequence[str],
    sources: Sequence[str],
) -> Any:
    """
    插入多条 chunk（按列组织数据）。
    """
    if not (len(chunk_ids) == len(embeddings) == len(contents) == len(sources)):
        raise ValueError("chunk 各列长度必须一致")
    return collection.insert([list(chunk_ids), list(embeddings), list(contents), list(sources)])


def search_chunks(
    collection: Collection,
    *,
    query_vectors: List[List[float]],
    cfg: Day6MilvusConfig,
    top_k: int,
) -> Any:
    """向量相似度检索（返回 PyMilvus SearchResult）。"""
    search_params = {"metric_type": cfg.metric_type, "params": {}}
    return collection.search(
        data=query_vectors,
        anns_field=VECTOR_FIELD,
        param=search_params,
        limit=top_k,
        output_fields=[PK_FIELD, CONTENT_FIELD, SOURCE_FIELD],
    )


def embedder_and_dim(
    ecfg: Optional[OllamaEmbedConfig] = None,
) -> Tuple[Any, int]:
    """
    创建嵌入模型，并用一次 probe 探测真实向量维度。
    """
    embedder = create_ollama_embedder(ecfg)
    probe = embed_query_text(embedder, "dim_probe")
    return embedder, len(probe)


def ingest_chunks_to_milvus(
    chunks: Sequence[str],
    *,
    source_label: str,
    cfg: Optional[Day6MilvusConfig] = None,
    ecfg: Optional[OllamaEmbedConfig] = None,
    reset_collection: bool = False,
) -> Tuple[Day6MilvusConfig, int]:
    """
    只负责“把 chunks 写入 Milvus”，不关心 chunks 怎么来的（清洗/分块属于上层流程）。
    """
    cfg = cfg or Day6MilvusConfig()
    embedder, dim = embedder_and_dim(ecfg)
    cfg = replace(cfg, vector_dim=dim)
    bridge = to_day5_milvus_cfg(cfg)

    connect_milvus(bridge)
    try:
        if reset_collection:
            drop_collection(cfg)
        coll = open_or_create_collection(cfg)

        ids = [f"{uuid.uuid4().hex[:12]}" for _ in chunks]
        vectors = embed_documents_texts(embedder, list(chunks))
        for i, v in enumerate(vectors):
            assert_vector_dim(v, cfg.vector_dim, context=f"chunk#{i}")

        sources = [source_label[:500]] * len(chunks)
        insert_chunks(
            coll,
            chunk_ids=ids,
            embeddings=vectors,
            contents=list(chunks),
            sources=sources,
        )
        coll.flush()
        ensure_vector_index_and_load(coll, bridge)
        coll.release()
        return cfg, len(chunks)
    finally:
        disconnect_milvus(bridge)


def query_chunks_from_milvus(
    question: str,
    *,
    sub_queries: Sequence[str],
    cfg: Optional[Day6MilvusConfig] = None,
    ecfg: Optional[OllamaEmbedConfig] = None,
    top_k_per_sub: int = 4,
) -> List[Dict[str, Any]]:
    """
    只负责“从 Milvus 检索 chunks”（多子问题、多次 search、再合并去重）。

    返回结构尽量保持与原 Day6 一致：
    - chunk_id/content/source/distance/matched_sub_query
    """
    cfg = cfg or Day6MilvusConfig()
    embedder, dim = embedder_and_dim(ecfg)
    cfg = replace(cfg, vector_dim=dim)
    bridge = to_day5_milvus_cfg(cfg)

    connect_milvus(bridge)
    try:
        coll = ensure_collection_ready(cfg)
        best: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        for sq in sub_queries:
            qvec = embed_query_text(embedder, sq)
            assert_vector_dim(qvec, cfg.vector_dim, context="子问题向量")
            res = search_chunks(coll, query_vectors=[qvec], cfg=cfg, top_k=top_k_per_sub)
            for hits in res:
                for hit in hits:
                    e = hit.entity
                    cid = e.get(PK_FIELD)
                    if not cid:
                        continue
                    dist = float(hit.distance)
                    row = {
                        PK_FIELD: cid,
                        CONTENT_FIELD: e.get(CONTENT_FIELD, ""),
                        SOURCE_FIELD: e.get(SOURCE_FIELD, ""),
                        "distance": dist,
                        "matched_sub_query": sq,
                        "backend": "milvus",
                    }
                    if cid not in best or dist < best[cid][0]:
                        best[cid] = (dist, row)
        coll.release()
        ranked = sorted(best.values(), key=lambda x: x[0])
        return [r[1] for r in ranked]
    finally:
        disconnect_milvus(bridge)

