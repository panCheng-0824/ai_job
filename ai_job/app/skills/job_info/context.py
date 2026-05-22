"""
检索与分析流程的共享上下文、HTTP 请求字段读取。

``RecommendRunCtx`` 贯穿：查询改写 → 语义缓存 → 知识库检索 →（可选）写回响应。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RecommendRunCtx:
    """
    单次岗位推荐请求的不可变上下文。

    Attributes:
        raw_query: 用户原始自然语言诉求；写入 API 响应的 ``query`` 字段。
        rag_q: 经 ``rewrite_job_query_for_rag`` 得到的检索短句；仅用于 GrepRAG/LightRAG。
        rewrite: ``{"raw_query", "rag_query"}``，写入 ``rag.rewrite`` 供前端/日志对照。
    """

    raw_query: str
    rag_q: str
    rewrite: Dict[str, str]


def rag_rewrite_meta(raw_q: str, rag_q: str) -> Dict[str, str]:
    """
    构造 ``rag.rewrite`` 对照信息。

    便于排查「用户说了什么」与「实际拿去检索的是什么」是否一致。
    """
    return {"raw_query": (raw_q or "").strip(), "rag_query": (rag_q or "").strip()}


def payload_field(payload: Any, name: str, default: Any = "") -> Any:
    """
    从 Pydantic 模型（如 ``JobInfoQueryRequest``）或普通 dict 读取字段。

    用于 pipeline 统一处理 HTTP 入参，避免与具体 schema 强耦合。
    """
    if hasattr(payload, name):
        return getattr(payload, name, default)
    if isinstance(payload, dict):
        return payload.get(name, default)
    return default
