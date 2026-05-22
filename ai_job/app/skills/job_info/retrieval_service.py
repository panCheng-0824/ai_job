"""
知识库检索入口与 Agent Markdown 工具。

职责分离
--------
- ``build_recommend_ctx``：查询改写，产出 ``RecommendRunCtx``（供缓存指纹与检索共用）
- ``recommend_from_ctx``：在已有 ctx 上检索，避免重复改写
- ``recommend_jobs_and_companies_async``：改写 + 检索（不含 LLM、不含缓存）
"""

from __future__ import annotations

from typing import Any, Dict

from app.skills.job_info.constants import (
    MARKDOWN_GREPRAG_TOP_K,
    RETRIEVAL_TOP_K_FACTOR,
    RETRIEVAL_TOP_K_MIN,
)
from app.skills.job_info.context import RecommendRunCtx, rag_rewrite_meta
from app.skills.job_info.kb_retrieval import recommend_via_greprag, recommend_via_lightrag
from app.skills.job_info.retrieval_payload import empty_retrieval_response
from app.skills.job_rag_query_rewrite import (
    rewrite_job_query_for_rag,
    rewrite_job_query_sync,
)


async def build_recommend_ctx(query: str, student_context: str = "") -> RecommendRunCtx:
    """
    改写用户 query，构造 ``RecommendRunCtx``。

    语义缓存与知识库检索应共用同一份 ctx，保证：
    - 缓存指纹中的 rag_q 与真实检索句一致
    - 响应中的 query 仍为 raw_query（用户原句）
    """
    raw_query = (query or "").strip()
    if not raw_query:
        return RecommendRunCtx(
            raw_query="",
            rag_q="",
            rewrite=rag_rewrite_meta("", ""),
        )
    rag_q, raw_stored = await rewrite_job_query_for_rag(raw_query, student_context)
    return RecommendRunCtx(
        raw_query=raw_stored,
        rag_q=rag_q,
        rewrite=rag_rewrite_meta(raw_stored, rag_q),
    )


async def recommend_from_ctx(
    ctx: RecommendRunCtx,
    *,
    top_n_jobs: int = 5,
    use_rag: bool = True,
) -> Dict[str, Any]:
    """
    在已有 ctx 上执行知识库检索（不再调用改写模型）。

    Args:
        ctx: 含 rag_q（检索句）与 raw_query（原句）
        top_n_jobs: 用于推算 top_k = max(40, top_n_jobs * 4)
        use_rag: True → LightRAG；False → GrepRAG
    """
    if not (ctx.raw_query or "").strip():
        return empty_retrieval_response()
    top_k = max(RETRIEVAL_TOP_K_MIN, top_n_jobs * RETRIEVAL_TOP_K_FACTOR)
    if not use_rag:
        return await recommend_via_greprag(ctx, top_k=top_k)
    return await recommend_via_lightrag(ctx, top_k=top_k)


async def recommend_jobs_and_companies_async(
    query: str,
    *,
    top_n_jobs: int = 5,
    top_n_companies: int = 3,
    use_rag: bool = True,
    student_context: str = "",
    only_need_context: bool = False,
) -> Dict[str, Any]:
    """
    异步检索入口：改写 → GrepRAG / LightRAG → 返回 rag 素材（jobs 为空）。

    不含语义缓存与 LLM；完整 HTTP 路径请用 ``run_job_info_query_async``。

    only_need_context / top_n_companies：保留 API 兼容，当前逻辑未单独使用。
    """
    _ = (only_need_context, top_n_companies)
    ctx = await build_recommend_ctx(query, student_context)
    return await recommend_from_ctx(ctx, top_n_jobs=top_n_jobs, use_rag=use_rag)


def recommend_jobs_and_companies_markdown(query: str, *, student_context: str = "") -> str:
    """
    LangChain Agent 工具 ``query_job_info`` 使用的同步接口。

    固定走 GrepRAG，避免在已有 asyncio 循环中嵌套异步调用；
    返回 Markdown，含用户原问题、改写句与检索正文。
    """
    raw = (query or "").strip()
    if not raw:
        return "（查询为空）"
    rag_q = rewrite_job_query_sync(raw, student_context)
    try:
        from app.rag.greprag.service import get_greprag_service

        gres = get_greprag_service().query(rag_q, top_k=MARKDOWN_GREPRAG_TOP_K)
    except Exception as e:
        return f"知识库检索失败：{e}"

    text = str((gres or {}).get("answer") or "").strip()
    if not text:
        return "_（知识库未命中，请调整关键词或确认语料已入库）_"
    return (
        f"## 知识库检索素材（供规划参考）\n\n"
        f"**用户原问题**：{raw}\n\n"
        f"**检索改写句**：{rag_q}\n\n"
        f"{text}"
    )
