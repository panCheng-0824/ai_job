"""
================================================================================
Neo4j KG Store（为“知识图谱 RAG”做准备）：独立封装
================================================================================

目标（学习版）
------------
你说的最终方向是“知识图谱 RAG”。要实现它，至少要把两件事工程化：

1) **把文本切片（chunk）写入 Neo4j**：作为图谱里的“证据载体”
2) **能根据用户问题在图谱里检索到相关 chunk**：把这些 chunk 作为 RAG 上下文的一部分

真正完整的 KG-RAG 通常还会包含：
- 实体/关系抽取（LLM 或规则）
- 图谱推理（多跳查询）
- 基于图谱的 query planning（LLM 生成 Cypher）

但作为 Day6 的下一步演进，我们先做一个“最小可用”的图谱检索层：
- 图模型：
    (:Source {name})
      -[:HAS_CHUNK]->
    (:Chunk {chunk_id, content})
- 索引：
    Neo4j Fulltext index：对 Chunk.content 建全文索引
- 检索：
    用问题文本做全文检索，返回最相关的 chunk 列表

这样做的好处：
- 你先把 Neo4j “接入流水线”跑通
- 后续再逐步加实体/关系抽取与 Cypher 推理，不会牵扯到 Day6 的其它代码
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class Neo4jConfig:
    """
    Neo4j 连接配置（默认读取环境变量，避免把密码写死在代码里）。

    建议你本地设置（示例）：
      export NEO4J_URI="bolt://localhost:7687"
      export NEO4J_USER="neo4j"
      export NEO4J_PASSWORD="你的密码"
    """

    uri: str = os.environ.get("NEO4J_URI", "")
    user: str = os.environ.get("NEO4J_USER", "neo4j")
    password: str = os.environ.get("NEO4J_PASSWORD", "")
    database: str = os.environ.get("NEO4J_DB", "neo4j")
    fulltext_index: str = os.environ.get("NEO4J_FT_INDEX", "study01_chunks_fulltext")


def _neo4j_available(cfg: Neo4jConfig) -> bool:
    """
    只要 uri 与 password 没配，就认为“Neo4j 未启用”，上层流程应当自动降级。
    """
    return bool(cfg.uri and cfg.password)


def _get_driver(cfg: Neo4jConfig):
    """
    延迟导入 neo4j driver：
    - 这样就算你机器没装 python neo4j 包，向量 RAG 也能正常跑
    - 只有你启用 Neo4j（配置了环境变量）才需要安装依赖：pip install neo4j
    """
    from neo4j import GraphDatabase  # type: ignore

    return GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))


def ensure_schema(cfg: Optional[Neo4jConfig] = None) -> None:
    """
    建立最小 schema：
    - Chunk(chunk_id) 唯一约束
    - Fulltext index（对 Chunk.content）
    """
    cfg = cfg or Neo4jConfig()
    if not _neo4j_available(cfg):
        return

    driver = _get_driver(cfg)
    try:
        with driver.session(database=cfg.database) as session:
            # Neo4j 5+ 支持 IF NOT EXISTS（如果你的版本更老，这句可能需要改）
            session.run(
                "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS "
                "FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE"
            )
            # fulltext index：用于“用问题文本在图里搜 chunk”
            session.run(
                f"CREATE FULLTEXT INDEX {cfg.fulltext_index} IF NOT EXISTS "
                "FOR (c:Chunk) ON EACH [c.content]"
            )
    finally:
        driver.close()


def upsert_chunks(
    chunks: Sequence[Dict[str, Any]],
    *,
    cfg: Optional[Neo4jConfig] = None,
) -> int:
    """
    写入/更新 chunks 到 Neo4j。

    输入 chunks 形状（建议）：
      {"chunk_id": "...", "content": "...", "source": "..."}

    图模型：
      (s:Source {name})-[:HAS_CHUNK]->(c:Chunk {chunk_id, content})
    """
    cfg = cfg or Neo4jConfig()
    if not _neo4j_available(cfg):
        return 0

    ensure_schema(cfg)
    driver = _get_driver(cfg)
    try:
        with driver.session(database=cfg.database) as session:
            q = """
            UNWIND $rows AS row
            MERGE (c:Chunk {chunk_id: row.chunk_id})
            SET c.content = row.content
            MERGE (s:Source {name: row.source})
            MERGE (s)-[:HAS_CHUNK]->(c)
            RETURN count(*) AS n
            """
            r = session.run(q, rows=list(chunks)).single()
            return int(r["n"]) if r else 0
    finally:
        driver.close()


def search_chunks_fulltext(
    question: str,
    *,
    cfg: Optional[Neo4jConfig] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    用全文索引检索相关 chunks。

    返回的字典字段尽量对齐 Milvus hits，便于在 Day6 里合并：
      - chunk_id/content/source/score/backend
    """
    cfg = cfg or Neo4jConfig()
    if not _neo4j_available(cfg):
        return []

    ensure_schema(cfg)
    driver = _get_driver(cfg)
    try:
        with driver.session(database=cfg.database) as session:
            q = f"""
            CALL db.index.fulltext.queryNodes($index, $q) YIELD node, score
            OPTIONAL MATCH (s:Source)-[:HAS_CHUNK]->(node)
            RETURN node.chunk_id AS chunk_id,
                   node.content AS content,
                   coalesce(s.name, "") AS source,
                   score AS score
            ORDER BY score DESC
            LIMIT $k
            """
            rows = session.run(
                q,
                index=cfg.fulltext_index,
                q=question,
                k=int(top_k),
            ).data()
            out: List[Dict[str, Any]] = []
            for r in rows:
                out.append(
                    {
                        "chunk_id": r.get("chunk_id", ""),
                        "content": r.get("content", ""),
                        "source": r.get("source", ""),
                        "score": float(r.get("score") or 0.0),
                        "backend": "neo4j",
                    }
                )
            return out
    finally:
        driver.close()

