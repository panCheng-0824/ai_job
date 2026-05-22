"""将 recomList 转为 API jobs / recommendation.recommended_jobs。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.skills.job_info.llm_parse import coerce_score


def jobs_from_recom_list(recom_list: List[Any]) -> List[Dict[str, Any]]:
    """大模型 recomList → jobs（不请求 server_job，字段来自模型 JSON）。"""
    out: List[Dict[str, Any]] = []
    for item in recom_list:
        if not isinstance(item, dict):
            continue
        jid = str(item.get("jobId") or item.get("job_id") or "").strip()
        title = str(item.get("jonName") or item.get("jobName") or "").strip()
        if not jid and not title:
            continue
        reason = str(item.get("reason") or "").strip()
        score = coerce_score(item.get("score"))
        city = str(item.get("city") or "").strip()
        salary = str(
            item.get("salaryRange") or item.get("salary_range_month") or ""
        ).strip()
        company = str(item.get("companyName") or item.get("company_name") or "").strip()
        category = str(item.get("jobCategory") or item.get("job_category") or "").strip()
        rel: Dict[str, Any] = (
            {"company_name": company, "credit_code": ""} if company else {}
        )
        out.append(
            {
                "job_id": jid,
                "job_title": title,
                "job_category": category,
                "city": city,
                "salary_range_month": salary,
                "skills_required": [],
                "company_relation": rel,
                "company_name": company,
                "score": score,
                "match_reasons": [reason] if reason else [],
            }
        )
    return out


def jobs_to_recommended_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """jobs → web_job recommendation.recommended_jobs。"""
    recommended: List[Dict[str, Any]] = []
    for j in jobs:
        reasons = [str(x).strip() for x in (j.get("match_reasons") or []) if str(x).strip()]
        match_reason = "；".join(reasons) if reasons else ""
        recommended.append(
            {
                "job_id": j.get("job_id", ""),
                "job_title": j.get("job_title", ""),
                "job_name": j.get("job_title", ""),
                "job_category": j.get("job_category", ""),
                "city": j.get("city", ""),
                "salary_range_month": j.get("salary_range_month", ""),
                "skills_required": j.get("skills_required", []),
                "company_relation": j.get("company_relation", {}),
                "company_name": j.get("company_name", ""),
                "score": j.get("score", 0),
                "match_reason": match_reason,
                "match_reasons": reasons,
            }
        )
    return recommended
