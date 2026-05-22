"""
LangChain Agent 工具专用：同步执行完整岗位推荐流水线，并格式化为 Markdown。

HTTP 路径仍使用 ``run_job_info_query_async``；本模块供 ``query_job_info_by_lightrag`` 调用，
避免在已有 asyncio 事件循环中嵌套 ``asyncio.run``。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.async_bridge import run_coroutine_sync
from app.skills.job_info.pipeline import run_job_info_query_async

# retrieval_only 时写入观测的检索正文上限（字符）
_RETRIEVAL_EXCERPT_MAX = 6000


def run_job_info_query_sync(payload: Any) -> Dict[str, Any]:
    """
    在同步上下文中运行 ``run_job_info_query_async``。

    通过 ``run_coroutine_sync`` 调度，保证与 LightRAG 单例使用同一类事件循环策略，
    避免在子线程 ``asyncio.run()`` 新建 loop 导致 PriorityQueue 跨 loop 报错。
    """
    return run_coroutine_sync(run_job_info_query_async(payload))


def format_job_info_query_markdown(result: Dict[str, Any]) -> str:
    """
    将 ``run_job_info_query_*`` 的 dict 响应压缩为 Agent 可读的 Markdown。

    优先输出 ``recommendation.recommended_jobs``；无结构化岗位时附检索摘要或原因说明。
    """
    query = str(result.get("query") or "").strip()
    rec = result.get("recommendation") if isinstance(result.get("recommendation"), dict) else {}
    llm = result.get("llm") if isinstance(result.get("llm"), dict) else {}
    rag = result.get("rag") if isinstance(result.get("rag"), dict) else {}
    rewrite = rag.get("rewrite") if isinstance(rag.get("rewrite"), dict) else {}

    lines: List[str] = ["## 岗位推荐结果（LightRAG + 分析）", ""]
    if query:
        lines.append(f"**用户诉求**：{query}")
    rag_q = str(rewrite.get("rag_query") or "").strip()
    if rag_q and rag_q != query:
        lines.append(f"**检索改写句**：{rag_q}")

    cache = result.get("cache")
    if isinstance(cache, dict) and cache.get("hit"):
        lines.append("_（命中语义相似缓存）_")

    reason = str(llm.get("reason") or "").strip()
    if reason:
        lines.append(f"**综合分析**：{reason}")

    llm_err = str(rag.get("llm_error") or "").strip()
    if llm_err:
        lines.append(f"**分析异常**：{llm_err}")

    status = str(rec.get("match_status") or "").strip()
    recommended = rec.get("recommended_jobs") if isinstance(rec.get("recommended_jobs"), list) else []

    if status == "matched" and recommended:
        lines.append("")
        lines.append(f"### 推荐岗位（共 {len(recommended)} 条）")
        for i, job in enumerate(recommended, 1):
            if not isinstance(job, dict):
                continue
            title = str(job.get("job_title") or job.get("job_name") or "未知岗位").strip()
            jid = str(job.get("job_id") or "").strip()
            city = str(job.get("city") or "").strip()
            salary = str(job.get("salary_range_month") or "").strip()
            company = str(job.get("company_name") or "").strip()
            score = job.get("score")
            match_reason = str(job.get("match_reason") or "").strip()
            meta_parts = [p for p in (city, salary) if p]
            meta = " / ".join(meta_parts) if meta_parts else ""
            head = f"{i}. **{title}**"
            if jid:
                head += f"（{jid}）"
            lines.append(head)
            if meta:
                lines.append(f"   - 城市/薪资：{meta}")
            if company:
                lines.append(f"   - 企业：{company}")
            if score is not None and str(score).strip():
                lines.append(f"   - 匹配分：{score}")
            if match_reason:
                lines.append(f"   - 理由：{match_reason}")
        lines.append("")
        lines.append(
            "_以上为知识库检索与模型分析后的参考岗位，不代表录用承诺；"
            "具体以企业招聘说明为准。_"
        )
        return "\n".join(lines)

    if status == "no_match":
        detail = rec.get("no_match_detail") if isinstance(rec.get("no_match_detail"), dict) else {}
        title = str(detail.get("title") or "暂无推荐").strip()
        causes = detail.get("causes") if isinstance(detail.get("causes"), list) else []
        suggestions = detail.get("suggestions") if isinstance(detail.get("suggestions"), list) else []
        lines.append("")
        lines.append(f"### {title}")
        for c in causes:
            c = str(c).strip()
            if c:
                lines.append(f"- {c}")
        if suggestions:
            lines.append("")
            lines.append("**建议**：")
            for s in suggestions:
                s = str(s).strip()
                if s:
                    lines.append(f"- {s}")
        return "\n".join(lines)

    retrieval_text = str(rag.get("retrieval_context") or "").strip()
    if retrieval_text:
        excerpt = retrieval_text
        if len(excerpt) > _RETRIEVAL_EXCERPT_MAX:
            excerpt = excerpt[:_RETRIEVAL_EXCERPT_MAX] + "\n\n…（检索正文已截断）"
        notes = rec.get("notes") if isinstance(rec.get("notes"), list) else []
        lines.append("")
        if notes:
            for n in notes:
                n = str(n).strip()
                if n:
                    lines.append(f"_{n}_")
        lines.append("")
        lines.append("### 知识库检索素材（未产出结构化岗位列表）")
        lines.append(excerpt)
        return "\n".join(lines)

    hint = str(rag.get("hint") or rag.get("error") or "").strip()
    lines.append("")
    lines.append("### 暂无可用结果")
    if hint:
        lines.append(hint)
    else:
        lines.append("未检索到岗位素材，请调整关键词或确认知识库已同步。")
    return "\n".join(lines)


def to_job_recommend_client_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """提取前端岗位推荐交互组件所需字段（与学生主页 ``job-info-query`` 对齐）。"""
    rec = result.get("recommendation") if isinstance(result.get("recommendation"), dict) else {}
    jobs = result.get("jobs") if isinstance(result.get("jobs"), list) else []
    if not jobs and isinstance(rec.get("recommended_jobs"), list):
        jobs = list(rec.get("recommended_jobs") or [])
    payload: Dict[str, Any] = {
        "jobs": jobs,
        "recommendation": rec,
        "rag": result.get("rag") if isinstance(result.get("rag"), dict) else {},
        "llm": result.get("llm") if isinstance(result.get("llm"), dict) else {},
    }
    cache = result.get("cache")
    if isinstance(cache, dict) and cache:
        payload["cache"] = cache
    return payload


def run_job_info_query_for_agent(payload: Any) -> str:
    """同步执行完整推荐并返回 Markdown（``query_job_info_by_lightrag`` 入口）。"""
    result = run_job_info_query_sync(payload)
    return format_job_info_query_markdown(result)
