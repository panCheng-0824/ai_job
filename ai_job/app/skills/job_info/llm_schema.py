"""大模型结构化输出：JSON Schema 与 response_format 配置。"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

# json_schema 模式下的 recomList 结构
RECOM_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "isrecommend": {
            "type": "string",
            "description": "yes 或 on 表示推荐，否则为 no",
        },
        "reason": {"type": "string", "description": "总体推荐或未推荐原因"},
        "recomList": {
            "type": "array",
            "description": "推荐岗位列表，按匹配度从高到低",
            "items": {
                "type": "object",
                "properties": {
                    "jobId": {"type": "string"},
                    "jonName": {"type": "string"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "reason": {"type": "string"},
                    "city": {"type": "string"},
                    "companyName": {"type": "string"},
                    "salaryRange": {"type": "string"},
                },
                "required": ["jobId", "jonName", "score", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["isrecommend", "reason", "recomList"],
    "additionalProperties": False,
}


def llm_response_format() -> Optional[Dict[str, Any]]:
    """
    环境变量 ``JOB_RAG_ANALYZE_RESPONSE_FORMAT``：
    - json_object（默认）
    - json_schema
    - none / off：不传 response_format
    """
    mode = (os.getenv("JOB_RAG_ANALYZE_RESPONSE_FORMAT", "json_object") or "json_object").strip().lower()
    if mode in ("none", "off", "disabled", "0", "false"):
        return None
    if mode == "json_schema":
        strict = os.getenv("JOB_RAG_ANALYZE_JSON_STRICT", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "job_recommendation",
                "strict": strict,
                "schema": RECOM_JSON_SCHEMA,
            },
        }
    return {"type": "json_object"}


def is_unsupported_response_format_error(exc: BaseException) -> bool:
    """当前模型/网关不支持 response_format 时可回退普通调用。"""
    msg = str(exc).lower()
    needles = (
        "response_format",
        "json_schema",
        "json_object",
        "structured outputs",
        "not supported",
        "unsupported",
        "invalid parameter",
    )
    return any(n in msg for n in needles)
