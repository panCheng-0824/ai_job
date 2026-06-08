"""
岗位推荐完整流水线：检索 + 大模型分析 + 可选语义缓存。

``run_job_info_query_async`` 为 HTTP ``/api/skills/job-info-query`` 的主入口；
``deal_data_by_llm`` 仅负责「已有检索素材 → LLM 结构化」，供单独调用或测试。
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from app.skills.job_info.constants import (
    DEFAULT_MIN_RECOMMEND_SCORE,
    DEFAULT_SCORE_BASELINE,
    DEFAULT_TOP_N_JOBS,
    MAX_TOP_N_JOBS,
)
from app.skills.job_info.context import payload_field
from app.skills.job_info.llm_client import analyze_retrieval_sync
from app.skills.job_info.llm_jobs import jobs_from_recom_list, jobs_to_recommended_jobs
from app.skills.job_info.llm_parse import is_recommend_yes, recom_list_from_parsed
from app.skills.job_info.recommendation import (
    build_recommendation_matched,
    build_recommendation_no_match,
    decorate_response,
)
from app.skills.job_info.retrieval_service import build_recommend_ctx, recommend_from_ctx
from app.skills.job_info import semantic_cache

log = logging.getLogger(__name__)


def _llm_disabled() -> bool:
    """为 True 时跳过 LLM 分析，仅返回检索结果 + decorate（retrieval_only）。"""
    return os.getenv("JOB_RAG_ANALYZE_DISABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _payload_bool(value: Any, *, default: bool) -> bool:
    """解析请求体中的布尔字段（支持 bool 或 0/1 字符串）。"""
    if isinstance(value, bool):
        return value
    s = str(value or "").strip().lower()
    if not s:
        return default
    return s in ("1", "true", "yes", "on")


def _clamp_score(value: Any, *, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(0, min(100, n))


def resolve_recommend_options(payload: Any) -> Dict[str, Any]:
    """解析 HTTP 请求中的推荐配置（与前端岗位推荐面板一致）。"""
    use_profile = _payload_bool(
        payload_field(payload, "use_student_profile", True), default=True
    )
    raw_ctx = str(payload_field(payload, "student_context", "") or "").strip()
    top_n_raw = payload_field(payload, "top_n_jobs", DEFAULT_TOP_N_JOBS)
    try:
        top_n_jobs = max(1, min(MAX_TOP_N_JOBS, int(top_n_raw or DEFAULT_TOP_N_JOBS)))
    except (TypeError, ValueError):
        top_n_jobs = DEFAULT_TOP_N_JOBS
    return {
        "use_student_profile": use_profile,
        "student_context": raw_ctx if use_profile else "",
        "score_baseline": _clamp_score(
            payload_field(payload, "score_baseline", DEFAULT_SCORE_BASELINE),
            default=DEFAULT_SCORE_BASELINE,
        ),
        "min_recommend_score": _clamp_score(
            payload_field(payload, "min_recommend_score", DEFAULT_MIN_RECOMMEND_SCORE),
            default=DEFAULT_MIN_RECOMMEND_SCORE,
        ),
        "top_n_jobs": top_n_jobs,
    }


def _recommend_options_meta(opts: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "use_student_profile": bool(opts.get("use_student_profile")),
        "score_baseline": int(opts.get("score_baseline", DEFAULT_SCORE_BASELINE)),
        "min_recommend_score": int(opts.get("min_recommend_score", DEFAULT_MIN_RECOMMEND_SCORE)),
        "top_n_jobs": int(opts.get("top_n_jobs", DEFAULT_TOP_N_JOBS)),
    }


def _filter_jobs_by_score(
    jobs: list, *, min_score: int, top_n: int
) -> list:
    filtered = [j for j in jobs if int(j.get("score") or 0) >= min_score]
    filtered.sort(key=lambda j: int(j.get("score") or 0), reverse=True)
    return filtered[:top_n]


def _use_semantic_cache_payload(payload: Any) -> bool:
    """
    是否使用语义相似缓存。

    - ``use_semantic_cache`` 默认 True（前端勾选「使用语义缓存」）
    - ``skip_cache=True`` 时强制关闭（兼容旧参数）
    """
    if _payload_bool(payload_field(payload, "skip_cache", False), default=False):
        return False
    return _payload_bool(payload_field(payload, "use_semantic_cache", True), default=True)


def _cache_active(payload: Any) -> bool:
    """环境变量开启且请求允许时，才读写语义缓存。"""
    return semantic_cache.cache_enabled() and _use_semantic_cache_payload(payload)


async def deal_data_by_llm(data: Dict[str, Any], payload: Any) -> Dict[str, Any]:
    """
    在检索结果上调用大模型分析素材，合并为完整 API 响应。

    步骤：
    1. 无 ``rag.retrieval_context`` → ``decorate_response``（retrieval_only / no_match）
    2. 有素材 → ``analyze_retrieval_sync`` → 解析 recomList → ``jobs_from_recom_list``
    3. LLM 异常 → 保留检索体，``rag.llm_error``，recommendation 仍为检索态

    注意：岗位字段来自模型 JSON，**不**请求 server_job 拉详情。
    """
    opts = resolve_recommend_options(payload)
    query = str(payload_field(payload, "query", "") or "").strip()
    student_context = str(opts["student_context"] or "").strip()
    top_n_jobs = int(opts["top_n_jobs"])
    min_score = int(opts["min_recommend_score"])
    score_baseline = int(opts["score_baseline"])
    use_profile = bool(opts["use_student_profile"])
    options_meta = _recommend_options_meta(opts)

    rag = data.get("rag") or {}
    retrieval_text = str(rag.get("retrieval_context") or "").strip()

    if not rag.get("enabled") or not retrieval_text:
        out = decorate_response(data)
        out["recommend_options"] = options_meta
        return out

    if _llm_disabled():
        out = decorate_response(data)
        out["recommend_options"] = options_meta
        return out

    try:
        parsed = await asyncio.to_thread(
            analyze_retrieval_sync,
            query,
            student_context,
            retrieval_text,
            score_baseline=score_baseline,
            use_student_profile=use_profile,
        )
    except Exception as e:
        log.warning("岗位素材 LLM 分析失败: %s", e, exc_info=True)
        out = decorate_response(data)
        rag_out = dict(out.get("rag") or {})
        rag_out["llm_error"] = str(e)
        out["rag"] = rag_out
        out["recommend_options"] = options_meta
        return out

    recom_list = recom_list_from_parsed(parsed)
    llm_summary: Dict[str, Any] = {
        "isrecommend": parsed.get("isrecommend"),
        "reason": parsed.get("reason"),
    }

    if not is_recommend_yes(parsed.get("isrecommend")) or not recom_list:
        reason = str(parsed.get("reason") or "模型未给出可推荐岗位").strip()
        return {
            **data,
            "jobs": [],
            "companies": [],
            "llm": llm_summary,
            "recommend_options": options_meta,
            "recommendation": build_recommendation_no_match(data, causes=[reason]),
        }

    jobs_all = jobs_from_recom_list(recom_list)
    jobs = _filter_jobs_by_score(jobs_all, min_score=min_score, top_n=top_n_jobs)
    recommended = jobs_to_recommended_jobs(jobs)

    if jobs:
        rec = build_recommendation_matched(data, recommended)
    else:
        rec = build_recommendation_no_match(
            data,
            causes=[
                f"模型给出的岗位均未达到最低推荐分数 {min_score} 分（评分基准 {score_baseline} 分）。"
            ],
            suggestions=[
                "可适当降低「最低推荐分数」后重试。",
                "或调整岗位诉求关键词以扩大检索范围。",
            ],
        )

    return {
        **data,
        "jobs": jobs,
        "companies": [],
        "llm": llm_summary,
        "recommend_options": options_meta,
        "recommendation": rec,
    }


async def run_job_info_query_async(payload: Any) -> Dict[str, Any]:
    """
    HTTP 主路径：改写 →（可选）语义缓存 → 检索 → LLM → 写缓存。

    流程说明：
    1. ``build_recommend_ctx``：得到 ``RecommendRunCtx``（raw_query / rag_q / rewrite）
    2. ``build_scope``：按引擎、KB 版本、top_n、分析模型等划分缓存桶
    3. ``semantic_cache.lookup``：命中则直接返回，响应顶层带 ``cache`` 字段
    4. 未命中：``recommend_from_ctx`` → ``deal_data_by_llm``
    5. 成功且有检索正文时 ``semantic_cache.store`` 写入完整结果

    语义缓存：请求 ``use_semantic_cache=true``（默认）且环境变量 ``JOB_INFO_SEM_CACHE_ENABLED=1``。
    """
    query = str(payload_field(payload, "query", "") or "").strip()
    if not query:
        from app.skills.job_info.retrieval_payload import empty_retrieval_response

        return decorate_response(empty_retrieval_response())

    opts = resolve_recommend_options(payload)
    student_context = str(opts["student_context"] or "").strip()
    top_n_jobs = int(opts["top_n_jobs"])
    top_n_companies = max(1, int(payload_field(payload, "top_n_companies", 3) or 3))
    use_rag = bool(payload_field(payload, "use_rag", True))
    use_profile = bool(opts["use_student_profile"])
    score_baseline = int(opts["score_baseline"])
    min_recommend_score = int(opts["min_recommend_score"])

    # 改写仅执行一次，ctx 供检索与缓存共用
    ctx = await build_recommend_ctx(query, student_context)
    scope = semantic_cache.build_scope(
        ctx,
        use_rag=use_rag,
        top_n_jobs=top_n_jobs,
        top_n_companies=top_n_companies,
        student_context=student_context,
        use_student_profile=use_profile,
        score_baseline=score_baseline,
        min_recommend_score=min_recommend_score,
    )

    # --- 读缓存（在线程池执行，避免阻塞 embed 同步调用）---
    if _cache_active(payload):
        hit = await asyncio.to_thread(
            semantic_cache.lookup,
            ctx,
            scope=scope,
            student_context=student_context,
        )
        if hit is not None:
            response, meta = hit
            return {**response, "cache": meta}

    # --- 完整链路 ---
    retrieval = await recommend_from_ctx(ctx, top_n_jobs=top_n_jobs, use_rag=use_rag)
    result = await deal_data_by_llm(retrieval, payload)

    # --- 写缓存：仅在有检索正文时保存，避免空结果污染缓存 ---
    if _cache_active(payload):
        if (ctx.raw_query or "").strip() and str(
            (result.get("rag") or {}).get("retrieval_context") or ""
        ).strip():
            await asyncio.to_thread(
                semantic_cache.store,
                ctx,
                scope=scope,
                response=result,
                student_context=student_context,
            )

    return result
