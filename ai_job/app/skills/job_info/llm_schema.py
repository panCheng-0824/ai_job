"""大模型结构化输出：JSON Schema 与 response_format 配置。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from model_cfg import ModelEntry, load_model_list

from app.skills.job_rag_query_rewrite import _select_chat_by_level

log = logging.getLogger(__name__)

# json_schema 模式下的 recomList 结构
RECOM_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "isrecommend": {
            "type": "string",
            "description": "yes 或 on 表示推荐，否则为 no",
        },
        "reason": {
            "type": "string",
            "description": "总体推荐说明（80–200 字）：筛选逻辑、与学生画像整体契合度及主要取舍",
        },
        "recomList": {
            "type": "array",
            "description": "推荐岗位列表，按匹配度从高到低",
            "items": {
                "type": "object",
                "properties": {
                    "jobId": {"type": "string，需要仔细验证，是一个32位的非纯数字的字符串"},
                    "jonName": {"type": "string"},
                    "score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "匹配分；须与 reason 中五维评分说明一致",
                    },
                    "reason": {
                        "type": "string",
                        "minLength": 300,
                        "description": "不少于300字；四段标题：【匹配结论】【评分依据】【素材依据】【差异提示】",
                    },
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


def format_recom_schema_for_prompt() -> str:
    """将 ``RECOM_JSON_SCHEMA`` 序列化为 Prompt 片段，供 ``json_object`` 模式注入。"""
    schema_text = json.dumps(RECOM_JSON_SCHEMA, ensure_ascii=False, indent=2)
    return (
        "【JSON Schema】输出须严格符合以下 schema（字段名、类型、必填项须一致；"
          "注意 jobid，是一个32位的非纯数字的字符串：\n"
        "勿在顶层或 recomList 元素中增加 schema 未定义的字段）：\n"
        f"{schema_text}"
    )


def select_analyze_model_entry() -> ModelEntry:
    """按 ``JOB_RAG_ANALYZE_MODEL_LEVEL`` 选取分析用 chat 模型条目。"""
    level = (os.getenv("JOB_RAG_ANALYZE_MODEL_LEVEL", "mid") or "mid").strip()
    return _select_chat_by_level(load_model_list(), level)


def _is_local_openai_gateway(api_url: str) -> bool:
    host = (urlparse(api_url).hostname or "").lower()
    if host in ("127.0.0.1", "localhost", "0.0.0.0"):
        return True
    if host.startswith("192.168.") or host.startswith("10."):
        return True
    return False


def infer_analyze_response_format_mode(entry: ModelEntry) -> str:
    """
    根据 ``JOB_RAG_ANALYZE_MODEL_LEVEL`` 对应条目推断 response_format 模式。

    优先读 modelCfg 可选字段 ``analyze_response_format``；
    未配置时按 ``model_api`` 启发式：本地网关 → none，DeepSeek → json_object，OpenAI → json_schema。
    """
    explicit = str(entry.get("analyze_response_format") or "").strip().lower()
    if explicit in ("json_object", "json_schema"):
        return explicit
    if explicit in ("none", "off", "disabled", "0", "false"):
        return "none"

    api = (entry.get("model_api") or "").strip()
    if _is_local_openai_gateway(api):
        return "none"
    api_l = api.lower()
    if "api.openai.com" in api_l:
        return "json_schema"
    if "deepseek.com" in api_l:
        return "json_object"
    if api_l.startswith("https://"):
        return "json_object"
    return "none"


def resolve_analyze_response_format_mode(entry: Optional[ModelEntry] = None) -> str:
    """
    解析岗位分析 response_format 模式。

    环境变量 ``JOB_RAG_ANALYZE_RESPONSE_FORMAT``：
    - auto（默认）：跟随 ``JOB_RAG_ANALYZE_MODEL_LEVEL`` 所选模型（modelCfg + 启发式）
    - json_object / json_schema / none：显式覆盖，不随档位变化
    """
    env_raw = (os.getenv("JOB_RAG_ANALYZE_RESPONSE_FORMAT") or "auto").strip().lower()
    if env_raw not in ("auto", "", "default"):
        if env_raw in ("none", "off", "disabled", "0", "false"):
            return "none"
        if env_raw in ("json_object", "json_schema"):
            return env_raw

    entry = entry or select_analyze_model_entry()
    mode = infer_analyze_response_format_mode(entry)
    log.debug(
        "岗位分析 response_format=auto → %s（level=%s, api=%s）",
        mode,
        entry.get("model_level"),
        entry.get("model_api"),
    )
    return mode


def llm_response_format(entry: Optional[ModelEntry] = None) -> Optional[Dict[str, Any]]:
    """
    返回传给 OpenAI 兼容 API 的 ``response_format`` 参数；``none`` 时返回 None。

    默认 ``JOB_RAG_ANALYZE_RESPONSE_FORMAT=auto``，与 ``JOB_RAG_ANALYZE_MODEL_LEVEL`` 联动。
    不支持时 ``llm_client`` 会自动回退为普通调用。
    """
    mode = resolve_analyze_response_format_mode(entry)
    if mode == "none":
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
