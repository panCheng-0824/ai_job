"""调用 OpenAI 兼容接口完成检索素材分析。"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from model_cfg import ModelEntry, load_model_list
from openai import OpenAI

from app.skills.job_info.llm_parse import parse_recom_json
from app.skills.job_info.llm_prompt import (
    analysis_system_message,
    build_analysis_prompt,
)
from app.skills.job_info.llm_schema import (
    is_unsupported_response_format_error,
    llm_response_format,
)
from app.skills.job_rag_query_rewrite import _select_chat_by_level

log = logging.getLogger(__name__)


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
            return (resp.choices[0].message.content or "").strip()
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


def analyze_retrieval_sync(
    user_query: str,
    student_context: str,
    retrieval_context: str,
    *,
    score_baseline: int = 85,
    use_student_profile: bool = True,
) -> Dict[str, Any]:
    """
    同步分析检索素材，返回规范化后的 recom JSON 对象。

    环境变量：JOB_RAG_ANALYZE_MODEL_LEVEL、JOB_RAG_ANALYZE_MAX_TOKENS、
    JOB_RAG_ANALYZE_RESPONSE_FORMAT、JOB_RAG_ANALYZE_JSON_STRICT。
    """
    level = (os.getenv("JOB_RAG_ANALYZE_MODEL_LEVEL", "mid") or "mid").strip()
    entry: ModelEntry = _select_chat_by_level(load_model_list(), level)
    client = OpenAI(api_key=entry["model_key"], base_url=entry["model_api"])

    response_format = llm_response_format()
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
            ),
        },
    ]
    content = invoke_chat_completion(
        client,
        model=entry["model_name"],
        messages=messages,
        temperature=0.2,
        max_tokens=int(os.getenv("JOB_RAG_ANALYZE_MAX_TOKENS", "2048")),
        response_format=response_format,
    )
    if not content:
        raise ValueError("模型返回为空")
    return parse_recom_json(content)
