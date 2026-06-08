"""OpenAI 兼容 LLM 调用封装，配置与项目 modelCfg.json 对齐。"""

from __future__ import annotations

import json
import logging
import os
import re

from langchain_core.messages import HumanMessage

from ai_search.step_log import log_phase, log_warn
from lc_agent import chat_model_from_entry, select_model_by_level
from model_cfg import ModelEntry, load_model_list

logger = logging.getLogger(__name__)

DEFAULT_MODEL_LEVEL = "mid"


def resolve_llm_entry(model_level: str = "") -> ModelEntry | None:
    """
    选择 LLM 配置：优先 .env 直配，否则按档位从 modelCfg.json 读取。

    环境变量：
    - ``AI_SEARCH_MODEL_LEVEL``：档位，默认 ``mid``
    - ``AI_SEARCH_MODEL_NAME`` / ``AI_SEARCH_MODEL_API`` / ``AI_SEARCH_MODEL_KEY``：
      三项均设置时覆盖 modelCfg.json
    """
    level = (
        model_level
        or os.getenv("AI_SEARCH_MODEL_LEVEL", DEFAULT_MODEL_LEVEL)
        or DEFAULT_MODEL_LEVEL
    ).strip()

    env_name = os.getenv("AI_SEARCH_MODEL_NAME", "").strip()
    env_api = os.getenv("AI_SEARCH_MODEL_API", "").strip()
    env_key = os.getenv("AI_SEARCH_MODEL_KEY", "").strip()
    if env_name and env_api and env_key:
        entry: ModelEntry = {
            "model_type": "chat",
            "model_level": level,
            "model_provider": (
                os.getenv("AI_SEARCH_MODEL_PROVIDER", "openai").strip() or "openai"
            ),
            "model_name": env_name,
            "model_api": env_api,
            "model_key": env_key,
        }
        log_phase(
            logger,
            "LLM",
            "模型配置(来源=.env直配)",
            model=env_name,
            level=level,
        )
        return entry

    try:
        entries = load_model_list()
    except Exception as exc:
        log_warn(logger, "LLM", "读取 modelCfg.json 失败", error=str(exc))
        return None

    if not entries:
        log_warn(logger, "LLM", "modelCfg.json 无可用模型")
        return None

    entry = select_model_by_level(entries, level)
    log_phase(
        logger,
        "LLM",
        "模型配置(来源=modelCfg.json)",
        model=entry.get("model_name", ""),
        level=level,
        base_url=entry.get("model_api", ""),
    )
    return entry


def get_llm(
    *,
    model_level: str = "",
    entry: ModelEntry | None = None,
    temperature: float = 0.1,
):
    """返回 ChatOpenAI 实例；失败返回 None。"""
    resolved = entry or resolve_llm_entry(model_level)
    if resolved is None:
        return None

    try:
        return chat_model_from_entry(resolved, temperature=temperature)
    except Exception as exc:
        log_warn(logger, "LLM", "初始化 ChatOpenAI 失败", error=str(exc))
        return None


def invoke_text(
    prompt: str,
    *,
    model_level: str = "",
    purpose: str = "general",
) -> str | None:
    entry = resolve_llm_entry(model_level)
    if entry is None:
        return None

    llm = get_llm(entry=entry)
    if llm is None:
        return None

    log_phase(
        logger,
        "LLM",
        "开始调用",
        purpose=purpose,
        model=entry.get("model_name", ""),
        prompt_len=len(prompt),
    )
    try:
        msg = llm.invoke([HumanMessage(content=prompt)])
        content = getattr(msg, "content", msg)
        text = str(content).strip()
        log_phase(
            logger,
            "LLM",
            "调用成功",
            purpose=purpose,
            response_len=len(text),
            preview=(text[:80] + "…") if len(text) > 80 else text,
        )
        return text
    except Exception as exc:
        log_warn(logger, "LLM", "调用失败", purpose=purpose, error=str(exc))
        return None


def parse_json_from_llm(text: str | None) -> dict | list | None:
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
    return None
