"""从 server_job HTTP 拉取岗位/企业：推荐主路径为按 id 拉详情（/api/jobs/{id}、/api/companies/{id}），
辅以关键词搜索（/api/data/search）；全量 list 接口仅保留给调试或脚本使用。"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Set
from urllib.parse import quote, quote_plus

log = logging.getLogger(__name__)


def get_server_job_base_url() -> str:
    return (os.getenv("SERVER_JOB_BASE_URL") or os.getenv("AI_JOB_SERVER_JOB_BASE_URL") or "").strip().rstrip("/")


def _http_timeout() -> float:
    try:
        return float(os.getenv("SERVER_JOB_HTTP_TIMEOUT", "12"))
    except ValueError:
        return 12.0


def _fetch_json(path: str) -> Any:
    base = get_server_job_base_url()
    if not base:
        return None
    url = f"{base}{path}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=_http_timeout()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log.warning("server_job HTTP 错误 url=%s code=%s", url, e.code)
        return None
    except Exception as e:
        log.warning("server_job 请求失败 url=%s err=%s", url, e)
        return None


def fetch_jobs_raw() -> List[Dict[str, Any]]:
    data = _fetch_json("/api/jobs")
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def fetch_companies_raw() -> List[Dict[str, Any]]:
    data = _fetch_json("/api/companies")
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def normalize_biz_job(row: Dict[str, Any]) -> Dict[str, Any]:
    """将 BizJobsInfo JSON（Spring 默认 camelCase）转为 job_info_query 内部结构。"""
    jid = str(row.get("id") or "").strip()
    kw = row.get("useKeyWords") or ""
    skills = [s.strip() for s in str(kw).replace("，", ",").split(",") if s.strip()]
    desc = str(row.get("content") or row.get("postingTitle") or row.get("html") or "")[:4000]
    return {
        "job_id": jid,
        "job_title": row.get("jobName") or "",
        "job_category": row.get("jobType") or "",
        "city": row.get("address") or "",
        "district": row.get("area") or "",
        "salary_range_month": row.get("salaryRange") or "",
        "skills_required": skills,
        "job_description": desc,
        "company_relation": {
            "company_name": row.get("companyName") or "",
            "credit_code": str(row.get("companyId") or "").strip(),
        },
    }


def normalize_biz_company(row: Dict[str, Any]) -> Dict[str, Any]:
    cc = str(row.get("id") or "").strip()
    return {
        "credit_code": cc,
        "company_name": row.get("companyName") or "",
        "industry": row.get("area") or row.get("companyType") or "",
        "employee_count_range": row.get("companySize") or "",
    }


def fetch_job_raw(job_id: str) -> Optional[Dict[str, Any]]:
    """GET /api/jobs/{jobId}，返回单条 BizJobsInfo 字典；404 或失败时为 None。"""
    jid = str(job_id).strip()
    if not jid:
        return None
    data = _fetch_json(f"/api/jobs/{quote(jid, safe='')}")
    return data if isinstance(data, dict) else None


def fetch_company_raw(credit_code: str) -> Optional[Dict[str, Any]]:
    """GET /api/companies/{creditCode}；不存在或失败时为 None。"""
    cc = str(credit_code).strip()
    if not cc:
        return None
    data = _fetch_json(f"/api/companies/{quote(cc, safe='')}")
    return data if isinstance(data, dict) else None


def load_jobs_by_ids_ordered(job_ids: Iterable[str], *, max_fetch: int = 40) -> List[Dict[str, Any]]:
    """按给定 id 顺序逐个拉取岗位详情（去重），最多成功拉取 max_fetch 条。"""
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for raw in job_ids:
        if len(out) >= max_fetch:
            break
        jid = str(raw).strip()
        if not jid or jid in seen:
            continue
        seen.add(jid)
        row = fetch_job_raw(jid)
        if row:
            out.append(normalize_biz_job(row))
    return out


def search_job_ids(keyword: str, *, limit: int = 30) -> List[str]:
    """GET /api/data/search?scope=job，返回岗位 id 列表（顺序与接口 jobs 数组一致）。"""
    q = (keyword or "").strip()
    if not q:
        return []
    lim = max(1, min(int(limit), 100))
    path = f"/api/data/search?keyword={quote_plus(q)}&scope=job&limit={lim}"
    data = _fetch_json(path)
    if not isinstance(data, dict):
        return []
    jobs = data.get("jobs") or []
    out: List[str] = []
    seen: Set[str] = set()
    for item in jobs:
        if not isinstance(item, dict):
            continue
        jid = str(item.get("job_id") or "").strip()
        if jid and jid not in seen:
            seen.add(jid)
            out.append(jid)
    return out


def load_company_index_by_credit_codes(credit_codes: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """按企业 id 逐个拉详情，构建 credit_code -> 规范化企业字典。"""
    out: Dict[str, Dict[str, Any]] = {}
    for cc in credit_codes:
        cc = str(cc).strip()
        if not cc or cc in out:
            continue
        row = fetch_company_raw(cc)
        if row:
            out[cc] = normalize_biz_company(row)
    return out


def load_jobs_from_server() -> List[Dict[str, Any]]:
    """全量岗位列表（仅调试或特殊脚本使用；推荐主路径请用 load_jobs_by_ids_ordered / search_job_ids）。"""
    return [normalize_biz_job(r) for r in fetch_jobs_raw() if str(r.get("id") or "").strip()]


def load_companies_from_server() -> List[Dict[str, Any]]:
    """全量企业列表（仅调试或特殊脚本使用）。"""
    return [normalize_biz_company(r) for r in fetch_companies_raw() if str(r.get("id") or "").strip()]
