"""本地 JSON 学生 / 企业 / 岗位 / 用户模型数据加载与检索。"""

import json
import random
from pathlib import Path
from typing import Any, Dict, List

from app.portal.errors import PortalError
from app.portal.paths import COMPANY_FILE, JOB_FILE, STUDENT_FILE, USERMODEL_FILE


def _load_json(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


students_data: List[Dict[str, Any]] = _load_json(STUDENT_FILE)
companies_data: List[Dict[str, Any]] = _load_json(COMPANY_FILE)
jobs_data: List[Dict[str, Any]] = _load_json(JOB_FILE)
user_models_data: List[Dict[str, Any]] = _load_json(USERMODEL_FILE)

students_index: Dict[str, Dict[str, Any]] = {item["student_id"]: item for item in students_data}
companies_index: Dict[str, Dict[str, Any]] = {item["credit_code"]: item for item in companies_data}
jobs_index: Dict[str, Dict[str, Any]] = {item["job_id"]: item for item in jobs_data}
user_models_index: Dict[str, Dict[str, Any]] = {item["usercode"]: item for item in user_models_data}


def _contains_keyword(fields: List[Any], keyword: str) -> bool:
    q = keyword.strip().lower()
    if not q:
        return False
    for field in fields:
        if q in str(field or "").lower():
            return True
    return False


def login_student(student_id: str) -> Dict[str, Any]:
    sid = student_id.strip()
    if not sid:
        raise PortalError("student_id 不能为空", 400)
    if sid not in students_index:
        raise PortalError("student_id 不存在", 404)
    return {"success": True, "student_id": sid, "message": "登录成功"}


def get_student_or_raise(student_id: str) -> Dict[str, Any]:
    student = students_index.get(student_id)
    if not student:
        raise PortalError("学生不存在", 404)
    return student


def get_company_or_raise(credit_code: str) -> Dict[str, Any]:
    company = companies_index.get(credit_code)
    if not company:
        raise PortalError("企业不存在", 404)
    return company


def get_job_or_raise(job_id: str) -> Dict[str, Any]:
    job = jobs_index.get(job_id)
    if not job:
        raise PortalError("岗位不存在", 404)
    return job


def search_data(keyword: str, scope: str, limit: int) -> Dict[str, Any]:
    q = (keyword or "").strip()
    if not q:
        raise PortalError("keyword 不能为空", 400)

    limit = max(1, min(int(limit), 100))
    normalized_scope = (scope or "all").strip().lower()
    allowed = {"all", "student", "job", "company"}
    if normalized_scope not in allowed:
        raise PortalError(f"scope 仅支持: {', '.join(sorted(allowed))}", 400)

    result: Dict[str, Any] = {
        "keyword": q,
        "scope": normalized_scope,
        "students": [],
        "jobs": [],
        "companies": [],
    }

    if normalized_scope in {"all", "student"}:
        matched_students: List[Dict[str, Any]] = []
        for item in students_data:
            if _contains_keyword(
                [
                    item.get("student_id", ""),
                    item.get("name", ""),
                    item.get("student_name", ""),
                    item.get("major", ""),
                    (item.get("education") or {}).get("major", ""),
                    (item.get("profile") or {}).get("major", ""),
                ],
                q,
            ):
                matched_students.append(
                    {
                        "student_id": item.get("student_id", ""),
                        "name": item.get("name", item.get("student_name", "")),
                        "major": item.get(
                            "major", (item.get("education") or {}).get("major", "")
                        ),
                    }
                )
            if len(matched_students) >= limit:
                break
        result["students"] = matched_students

    if normalized_scope in {"all", "job"}:
        matched_jobs: List[Dict[str, Any]] = []
        for item in jobs_data:
            relation = item.get("company_relation") or {}
            if _contains_keyword(
                [
                    item.get("job_id", ""),
                    item.get("job_title", ""),
                    item.get("city", ""),
                    item.get("district", ""),
                    relation.get("company_name", ""),
                ],
                q,
            ):
                matched_jobs.append(
                    {
                        "job_id": item.get("job_id", ""),
                        "job_title": item.get("job_title", ""),
                        "city": item.get("city", ""),
                        "district": item.get("district", ""),
                        "company_name": relation.get("company_name", ""),
                        "credit_code": relation.get("credit_code", ""),
                    }
                )
            if len(matched_jobs) >= limit:
                break
        result["jobs"] = matched_jobs

    if normalized_scope in {"all", "company"}:
        matched_companies: List[Dict[str, Any]] = []
        for item in companies_data:
            if _contains_keyword(
                [
                    item.get("credit_code", ""),
                    item.get("company_name", ""),
                    item.get("industry", ""),
                    item.get("company_address", ""),
                ],
                q,
            ):
                matched_companies.append(
                    {
                        "credit_code": item.get("credit_code", ""),
                        "company_name": item.get("company_name", ""),
                        "industry": item.get("industry", ""),
                    }
                )
            if len(matched_companies) >= limit:
                break
        result["companies"] = matched_companies

    result["total"] = (
        len(result["students"]) + len(result["jobs"]) + len(result["companies"])
    )
    return result


def list_user_models_for_api() -> List[Dict[str, Any]]:
    return [
        {
            "username": item.get("username", ""),
            "usercode": item.get("usercode", ""),
            "role_name": item.get("user_profile", {}).get("role_name", ""),
            "domain": item.get("user_profile", {}).get("domain", ""),
            "model_level": item.get("model_level", ""),
        }
        for item in user_models_data
    ]


def ensure_student_exists(student_id: str) -> None:
    sid = (student_id or "").strip()
    if not sid:
        raise PortalError("student_id 不能为空", 400)
    if sid not in students_index:
        raise PortalError("student_id 不存在", 404)


def ensure_user_model_exists(usercode: str) -> None:
    uc = (usercode or "").strip()
    if not uc:
        raise PortalError("usercode 不能为空", 400)
    if uc not in user_models_index:
        raise PortalError("user_model 不存在", 404)


def get_user_model_or_raise(usercode: str) -> Dict[str, Any]:
    uc = (usercode or "").strip()
    if not uc:
        raise PortalError("usercode 不能为空", 400)
    model = user_models_index.get(uc)
    if not model:
        raise PortalError("user_model 不存在", 404)
    return model


def build_new_chat_session(
    session_id: str, student_id: str, usercode: str, created_at_iso: str
) -> Dict[str, Any]:
    um = user_models_index[usercode]
    return {
        "session_id": session_id,
        "student_id": student_id,
        "usercode": usercode,
        "username": um.get("username", ""),
        "role_name": um.get("user_profile", {}).get("role_name", ""),
        "model_level": um.get("model_level", ""),
        "created_at": created_at_iso,
        "history": [],
    }


def random_session_id_for_student(student_id: str) -> Dict[str, Any]:
    sid = student_id.strip()
    if not sid:
        raise PortalError("student_id 不能为空", 400)
    if sid not in students_index:
        raise PortalError("student_id 不存在", 404)
    return {"session_id": f"{sid}-{random.randint(100000, 999999)}"}
