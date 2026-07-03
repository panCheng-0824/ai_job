"""调用 OpenAI 兼容接口完成检索素材分析。"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from model_cfg import ModelEntry, load_model_list
from openai import OpenAI

from app.skills.job_info.llm_parse import RecomJsonParseError, parse_recom_json
from app.skills.job_info.llm_prompt import (
    analysis_system_message,
    build_analysis_prompt,
)
from app.common.llm_call_log import log_llm_call_from_entry
from app.skills.job_info.llm_schema import (
    is_unsupported_response_format_error,
    llm_response_format,
    resolve_analyze_response_format_mode,
)
from app.skills.job_rag_query_rewrite import _select_chat_by_level

log = logging.getLogger(__name__)

_REPAIR_USER_MSG = (
    "上一段输出不是合法 JSON，无法被程序解析。请只输出一个 JSON 对象，"
    "不要 markdown 围栏、不要注释、不要其它说明。"
    "必含字段：isrecommend、reason、recomList；recomList 元素含 jobId、jonName、score、reason。"
)


def _parse_retry_enabled() -> bool:
    v = (os.getenv("JOB_RAG_ANALYZE_PARSE_RETRY", "1") or "1").strip().lower()
    return v in ("1", "true", "yes", "on")


def invoke_chat_completion(
    client: OpenAI,
    *,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    response_format: Optional[Dict[str, Any]],
) -> str:
    """chat.completions；不支持 response_format 时自动回退。"""
    base_kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        try:
            resp = client.chat.completions.create(
                **base_kwargs,
                response_format=response_format,
            )
            return (resp.choices[0].message.content or resp.choices[0].message.reasoning_content or "").strip()
        except Exception as e:
            if not is_unsupported_response_format_error(e):
                raise
            log.warning(
                "岗位分析 response_format=%s 不可用，回退普通调用: %s",
                response_format.get("type"),
                e,
            )
    resp = client.chat.completions.create(**base_kwargs)
    return (resp.choices[0].message.content or "").strip()


def _parse_or_repair(
    client: OpenAI,
    entry: ModelEntry,
    messages: List[Dict[str, str]],
    content: str,
    *,
    max_tokens: int,
    response_format: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """解析 recom JSON；失败且开启重试时，追加一轮修复提示再调模型。"""
    try:
        return parse_recom_json(content)
    except RecomJsonParseError as first_err:
        if not _parse_retry_enabled():
            raise
        log.warning(
            "岗位分析 JSON 解析失败，尝试修复重试: %s; preview=%s",
            first_err,
            first_err.raw_preview[:120],
        )
        repair_messages = list(messages) + [
            {"role": "assistant", "content": content},
            {"role": "user", "content": _REPAIR_USER_MSG},
        ]
        # 修复轮强制 json_object（若网关支持），提高二次成功率
        repair_format: Optional[Dict[str, Any]] = {"type": "json_object"}
        if response_format and response_format.get("type") == "json_schema":
            repair_format = response_format
        repaired = invoke_chat_completion(
            client,
            model=entry["model_name"],
            messages=repair_messages,
            temperature=0.1,
            max_tokens=max_tokens,
            response_format=repair_format,
        )
        if not repaired:
            raise first_err
        try:
            return parse_recom_json(repaired)
        except RecomJsonParseError as second_err:
            raise RecomJsonParseError(
                f"{first_err}; 修复重试后仍失败: {second_err}",
                raw_preview=second_err.raw_preview or first_err.raw_preview,
            ) from second_err


def analyze_retrieval_sync(
    user_query: str,
    student_context: str,
    retrieval_context: str,
    *,
    score_baseline: int = 85,
    use_student_profile: bool = True,
    score_dimensions: dict | None = None,
) -> Dict[str, Any]:
    """
    同步分析检索素材，返回规范化后的 recom JSON 对象。

    环境变量：JOB_RAG_ANALYZE_MODEL_LEVEL、JOB_RAG_ANALYZE_MAX_TOKENS、
    JOB_RAG_ANALYZE_RESPONSE_FORMAT、JOB_RAG_ANALYZE_JSON_STRICT、
    JOB_RAG_ANALYZE_PARSE_RETRY（解析失败是否修复重试，默认开）。
    """
    level = (os.getenv("JOB_RAG_ANALYZE_MODEL_LEVEL", "mid") or "mid").strip()
    entry: ModelEntry = _select_chat_by_level(load_model_list(), level)
    client = OpenAI(api_key=entry["model_key"], base_url=entry["model_api"])

    response_format_mode = resolve_analyze_response_format_mode(entry)
    response_format = llm_response_format(entry)
    include_json_schema = response_format_mode == "json_object"
    max_tokens = int(os.getenv("JOB_RAG_ANALYZE_MAX_TOKENS", "20480"))
    log_llm_call_from_entry(
        "岗位推荐-检索素材分析",
        entry,
        response_format=response_format,
        response_format_mode=response_format_mode,
        include_json_schema=include_json_schema,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": analysis_system_message(use_structured_format=bool(response_format)),
        },
        {
            "role": "user",
            "content": build_analysis_prompt(
                user_query,
                student_context,
                retrieval_context,
                score_baseline=score_baseline,
                use_student_profile=use_student_profile,
                score_dimensions=score_dimensions,
                include_json_schema=include_json_schema,
            ),
        },
    ]
    content = invoke_chat_completion(
        client,
        model=entry["model_name"],
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
        response_format=response_format,
    )
    if not content:
        raise ValueError("模型返回为空")
    return _parse_or_repair(
        client,
        entry,
        messages,
        content,
        max_tokens=max_tokens,
        response_format=response_format,
    )
