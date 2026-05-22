"""GrepRAG / LightRAG 检索实现。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.skills.job_info.context import RecommendRunCtx
from app.skills.job_info.retrieval_payload import (
    build_retrieval_payload,
    error_retrieval_response,
    normalize_greprag_contexts,
)

log = logging.getLogger(__name__)


async def recommend_via_greprag(ctx: RecommendRunCtx, *, top_k: int) -> Dict[str, Any]:
    """本地 Markdown 语料关键词检索。"""
    try:
        from app.rag.greprag.service import get_greprag_service

        gres = await asyncio.to_thread(
            lambda: get_greprag_service().query(ctx.rag_q, top_k=top_k)
        )
    except Exception as e:
        log.warning("GrepRAG 岗位检索失败: %s", e, exc_info=True)
        return error_retrieval_response(ctx, mode="greprag_error", detail=str(e))

    contexts = normalize_greprag_contexts((gres or {}).get("contexts"))
    context_text = str((gres or {}).get("answer") or "").strip()
    if not context_text and not contexts:
        return build_retrieval_payload(
            ctx,
            kb="greprag",
            enabled=False,
            mode="greprag_no_hits",
            context_text="",
            contexts=[],
            hint="GrepRAG 未检索到相关岗位文档，请调整关键词或确认语料已入库。",
        )

    return build_retrieval_payload(
        ctx,
        kb="greprag",
        enabled=True,
        mode="greprag_context",
        context_text=context_text,
        contexts=contexts,
        hint="已返回知识库检索素材；请结合 query（用户原句）由业务侧自定义模型分析。",
    )


async def recommend_via_lightrag(ctx: RecommendRunCtx, *, top_k: int) -> Dict[str, Any]:
    """LightRAG 混合检索，仅取上下文（不调用内置生成）。"""
    try:
        from app.rag.lightrag.service import LightRAGUnavailableError, get_lightrag_service
    except ImportError:
        return error_retrieval_response(ctx, mode="import_error", detail="LightRAG 未安装")

    try:
        svc = get_lightrag_service()
        context_text = await svc.query(
            ctx.rag_q,
            mode="mix",
            top_k=top_k,
            only_need_context=True,
        )
    except LightRAGUnavailableError as e:
        return error_retrieval_response(ctx, mode="unavailable", detail=str(e))
    except Exception as e:
        log.warning("LightRAG 岗位检索失败: %s", e, exc_info=True)
        return error_retrieval_response(ctx, mode="error", detail=str(e))

    text = str(context_text or "").strip()
    if not text:
        return build_retrieval_payload(
            ctx,
            kb="lightrag",
            enabled=False,
            mode="lightrag_no_hits",
            context_text="",
            hint="LightRAG 检索无上下文返回，请检查知识库是否已同步岗位或调整检索表述。",
        )

    return build_retrieval_payload(
        ctx,
        kb="lightrag",
        enabled=True,
        mode="lightrag_context",
        context_text=text,
        contexts=[],
        hint="已返回知识库检索素材；请结合 query（用户原句）由业务侧自定义模型分析。",
    )
