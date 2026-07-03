"""将 recomList 转为 API jobs / recommendation.recommended_jobs。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from app.skills.job_info.llm_parse import coerce_score
from app.skills.job_info.reason_format import parse_match_reason_sections

log = logging.getLogger(__name__)


def _normalize_job_id_key(raw: Any) -> str:
    return str(raw or "").strip().lower()


def _job_dedupe_key(job: Dict[str, Any]) -> str:
    """去重键：优先 job_id，否则 title+company。"""
    jid = _normalize_job_id_key(job.get("job_id") or job.get("id"))
    if jid:
        return f"id:{jid}"
    title = str(job.get("job_title") or job.get("job_name") or "").strip().lower()
    company = str(
        job.get("company_name")
        or (job.get("company_relation") or {}).get("company_name")
        or ""
    ).strip().lower()
    if title:
        return f"title:{title}|{company}"
    return ""


def _job_richness(job: Dict[str, Any]) -> Tuple[int, int, int]:
    """重复岗位保留更丰富的一条（分数、理由长度、字段完整度）。"""
    score = int(job.get("score") or 0)
    reasons = job.get("match_reasons")
    if isinstance(reasons, list) and reasons:
        reason_len = len(str(reasons[0] or ""))
    else:
        reason_len = len(str(job.get("match_reason") or ""))
    field_count = sum(
        1
        for key in ("job_title", "job_name", "city", "salary_range_month", "company_name")
        if str(job.get(key) or "").strip()
    )
    return score, reason_len, field_count


def dedupe_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    按 job_id 去重（小写归一化）；无 id 时按 title+company。
    同一键多条时保留分数更高、理由更完整的一条。
    """
    by_key: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        key = _job_dedupe_key(job)
        if not key:
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = job
            order.append(key)
        elif _job_richness(job) > _job_richness(existing):
            by_key[key] = job
    return [by_key[k] for k in order if k in by_key]


def finalize_match_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """API 最终输出前对 jobs / recommendation.recommended_jobs 去重并保持一致。"""
    out = dict(data)
    raw_jobs = list(out.get("jobs") or [])
    jobs = dedupe_jobs(raw_jobs)
    if len(jobs) != len(raw_jobs):
        log.info("岗位推荐输出去重：jobs %s → %s", len(raw_jobs), len(jobs))
    out["jobs"] = jobs

    rec = out.get("recommendation")
    if not isinstance(rec, dict):
        return out

    rec = dict(rec)
    if rec.get("match_status") == "matched" and jobs:
        rec["recommended_jobs"] = jobs_to_recommended_jobs(jobs)
    elif isinstance(rec.get("recommended_jobs"), list):
        raw_rec = list(rec.get("recommended_jobs") or [])
        deduped_rec = dedupe_jobs(raw_rec)
        if len(deduped_rec) != len(raw_rec):
            log.info(
                "岗位推荐输出去重：recommended_jobs %s → %s",
                len(raw_rec),
                len(deduped_rec),
            )
        rec["recommended_jobs"] = deduped_rec
    out["recommendation"] = rec
    return out


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
        sections = parse_match_reason_sections(reason)
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
                "match_reason_sections": sections,
            }
        )
    return dedupe_jobs(out)


def jobs_to_recommended_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """jobs → web_job recommendation.recommended_jobs。"""
    recommended: List[Dict[str, Any]] = []
    for j in jobs:
        reasons = [str(x).strip() for x in (j.get("match_reasons") or []) if str(x).strip()]
        match_reason = "；".join(reasons) if reasons else ""
        sections = j.get("match_reason_sections") or parse_match_reason_sections(match_reason)
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
                "match_reason_sections": sections,
            }
        )
    return recommended
