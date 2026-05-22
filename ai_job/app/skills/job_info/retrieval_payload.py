"""知识库检索结果的统一响应体组装。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.skills.job_info.constants import RETRIEVAL_PREVIEW_MAX
from app.skills.job_info.context import RecommendRunCtx, rag_rewrite_meta


def normalize_greprag_contexts(raw: Any) -> List[Dict[str, Any]]:
    """将 GrepRAG contexts 规范为 dict 列表。"""
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append({str(k): v for k, v in item.items()})
        else:
            out.append({"content": str(item)})
    return out


def build_retrieval_payload(
    ctx: RecommendRunCtx,
    *,
    kb: str,
    enabled: bool,
    mode: str,
    context_text: str,
    contexts: Optional[List[Dict[str, Any]]] = None,
    hint: str = "",
    error: str = "",
) -> Dict[str, Any]:
    """组装检索阶段 API 返回体（jobs/companies 恒为空）。"""
    text = (context_text or "").strip()
    norm_contexts = contexts or []
    preview = text[:RETRIEVAL_PREVIEW_MAX] if text else ""
    rag: Dict[str, Any] = {
        "enabled": enabled,
        "mode": mode,
        "rewrite": ctx.rewrite,
        "retrieval_context": text,
        "contexts": norm_contexts,
        "context_count": len(norm_contexts) if norm_contexts else (1 if text else 0),
        "answer_preview": preview,
    }
    if hint:
        rag["hint"] = hint
    if error:
        rag["error"] = error
    return {
        "query": ctx.raw_query,
        "data_source": f"{kb}_retrieval" if enabled else "server_job",
        "jobs": [],
        "companies": [],
        "rag": rag,
    }


def empty_retrieval_response() -> Dict[str, Any]:
    """用户 query 为空，未执行检索。"""
    rewrite = rag_rewrite_meta("", "")
    ctx = RecommendRunCtx(raw_query="", rag_q="", rewrite=rewrite)
    return build_retrieval_payload(
        ctx,
        kb="",
        enabled=False,
        mode="empty_query",
        context_text="",
        hint="用户诉求为空，未执行检索。",
    )


def error_retrieval_response(ctx: RecommendRunCtx, *, mode: str, detail: str) -> Dict[str, Any]:
    """知识库检索异常。"""
    return build_retrieval_payload(
        ctx,
        kb="",
        enabled=False,
        mode=mode,
        context_text="",
        error=detail,
        hint=f"知识库检索失败：{detail}",
    )
