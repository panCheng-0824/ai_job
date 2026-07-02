"""LightRAG 运行时依赖加载与模型函数构建。"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from typing import Any

from pydantic import BaseModel

from lc_agent.selection import select_model_by_type_and_level
from model_cfg import ModelEntry, load_model_list

from app.common.llm_call_log import log_llm_call_from_entry
from app.skills.job_info.llm_schema import is_unsupported_response_format_error

from .embedding_config import resolve_embedding_params

log = logging.getLogger(__name__)


class LightRAGUnavailableError(RuntimeError):
    """LightRAG 依赖不可用或运行环境不满足要求。"""


def load_light_rag_symbols() -> tuple[Any, Any, Any]:
    """惰性导入 LightRAG，避免环境不满足时进程启动即崩溃。"""
    if sys.version_info < (3, 10):
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raise LightRAGUnavailableError(
            f"LightRAG 运行环境不满足要求：当前 Python={current}，需要 Python>=3.10。"
            "请使用 Python 3.10+ 重建虚拟环境并重新安装 lightrag-hku。"
        )
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.llm.openai import openai_complete_if_cache, openai_embed
        log.info("LightRAG 运行时符号加载成功")
    except Exception as exc:  # pragma: no cover - depends on environment
        log.exception("LightRAG 运行时符号加载失败")
        raise LightRAGUnavailableError("LightRAG 不可用：请确保 Python>=3.10 且已安装 lightrag-hku。") from exc
    return LightRAG, QueryParam, (openai_complete_if_cache, openai_embed)


def select_llm_entry(model_level: str) -> ModelEntry:
    """根据配置选择模型：优先读取环境变量，缺失时回退 modelCfg.json。"""
    env_provider = os.getenv("LIGHTRAG_MODEL_PROVIDER", "openai").strip() or "openai"
    env_type = os.getenv("LIGHTRAG_MODEL_TYPE", "chat").strip() or "chat"
    env_level = os.getenv("LIGHTRAG_MODEL_LEVEL", model_level).strip() or model_level
    # 默认按 .env 指定的 type + level，从 modelCfg.json 选择模型。
    # 仅当 name/api/key 三项都配置时，才使用 .env 的直配模型。
    env_name = os.getenv("LIGHTRAG_MODEL_NAME", "").strip()
    env_api = os.getenv("LIGHTRAG_MODEL_API", "").strip()
    env_key = os.getenv("LIGHTRAG_MODEL_KEY", "").strip()
    if env_name and env_api and env_key:
        entry: ModelEntry = {
            "model_type": env_type,
            "model_level": env_level,
            "model_provider": env_provider,
            "model_name": env_name,
            "model_api": env_api,
            "model_key": env_key,
        }
        log.info("LightRAG 模型配置读取完成(来源=.env直配), type=%s, level=%s, model=%s", env_type, env_level, env_name)
        return entry
    entry = select_model_by_type_and_level(load_model_list(), model_type=env_type, level=env_level)
    log.info(
        "LightRAG 模型配置读取完成(来源=modelCfg.json), env_type=%s, env_level=%s, selected_model=%s",
        env_type,
        env_level,
        entry.get("model_name", ""),
    )
    return entry


def select_embedding_entry(model_level: str) -> ModelEntry | None:
    """按 embedding 类型与档位选择向量模型；无匹配时返回 None。"""
    entries = load_model_list()
    normalized_type = (os.getenv("LIGHTRAG_EMBED_TYPE", "embedding").strip() or "embedding")
    normalized_level = (os.getenv("LIGHTRAG_EMBED_LEVEL", model_level).strip() or model_level)
    log.info("LightRAG 开始按 type+level 选择 embedding 模型, type=%s, level=%s", normalized_type, normalized_level)
    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == normalized_type.lower() and entry.get("model_level") == normalized_level:
            log.info("LightRAG 命中 embedding 模型(同 type+level): %s", entry.get("model_name", ""))
            return entry
    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == normalized_type.lower():
            log.info("LightRAG 命中 embedding 模型(同 type 回退): %s", entry.get("model_name", ""))
            return entry
    log.warning("LightRAG 未找到 embedding 模型，将回退到 chat 模型")
    return None


def select_doc_clean_entry(model_level: str) -> ModelEntry | None:
    """按文档清洗配置的 type+level 选择模型；默认 type=chat，与 embedding 选择逻辑一致。"""
    entries = load_model_list()
    clean_type = (os.getenv("LIGHTRAG_DOC_CLEAN_TYPE", "chat").strip() or "chat")
    clean_level = (os.getenv("LIGHTRAG_DOC_CLEAN_LEVEL", model_level).strip() or model_level)
    log.info("LightRAG 开始按 type+level 选择文档清洗模型, type=%s, level=%s", clean_type, clean_level)
    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == clean_type.lower() and entry.get("model_level") == clean_level:
            log.info("LightRAG 命中文档清洗模型(同 type+level): %s", entry.get("model_name", ""))
            return entry
    for entry in entries:
        if str(entry.get("model_type", "chat")).strip().lower() == clean_type.lower():
            log.info("LightRAG 命中文档清洗模型(同 type 回退): %s", entry.get("model_name", ""))
            return entry
    log.warning("LightRAG 未找到文档清洗模型(type=%s)，将回退到 chat 模型条目", clean_type)
    return None


def _keyword_response_format() -> dict[str, str] | str | None:
    """
    关键词抽取时的 response_format（可选）。

    环境变量 ``LIGHTRAG_KW_RESPONSE_FORMAT``：none（默认）/ json_object / json。
    勿使用 LightRAG 内置的 GPTKeywordExtractionFormat，DeepSeek 等网关会返回 400。
    """
    mode = (os.getenv("LIGHTRAG_KW_RESPONSE_FORMAT", "none") or "none").strip().lower()
    if mode in ("none", "off", "0", "false", ""):
        return None
    if mode == "json_object":
        return {"type": "json_object"}
    if mode == "json":
        return "json"
    return None


def _strip_pydantic_response_format(kwargs: dict[str, Any]) -> None:
    """移除 Pydantic 类 response_format（会走 completions.parse，多数兼容网关不支持）。"""
    rf = kwargs.get("response_format")
    if isinstance(rf, type) and issubclass(rf, BaseModel):
        kwargs.pop("response_format", None)


def build_openai_funcs(entry: ModelEntry) -> tuple[Any, Any]:
    """构建 LightRAG 所需的 LLM 与向量嵌入异步函数。"""
    _, _, funcs = load_light_rag_symbols()
    openai_complete_if_cache, openai_embed = funcs
    log.info(
        "LightRAG 开始构建 OpenAI 兼容函数, chat_model=%s, base_url=%s",
        entry.get("model_name"),
        entry.get("model_api"),
    )

    async def _llm_model_func(
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list[dict[str, str]] | None = None,
        keyword_extraction: bool = False,
        **kwargs: Any,
    ) -> str:
        kw_extract = keyword_extraction or bool(kwargs.pop("keyword_extraction", False))
        _strip_pydantic_response_format(kwargs)
        if kw_extract:
            kwargs.pop("response_format", None)
            kw_rf = _keyword_response_format()
            if kw_rf is not None:
                kwargs["response_format"] = kw_rf

        scenario = "LightRAG-关键词抽取" if kw_extract else "LightRAG-对话生成"
        log_llm_call_from_entry(
            scenario,
            entry,
            response_format=kwargs.get("response_format"),
            keyword_extraction=kw_extract,
        )

        async def _invoke() -> str:
            return await openai_complete_if_cache(
                entry["model_name"],
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                api_key=entry["model_key"],
                base_url=entry["model_api"],
                # 新版 LightRAG 在 keyword_extraction=True 时会注入 GPTKeywordExtractionFormat
                keyword_extraction=False,
                **kwargs,
            )

        try:
            return await _invoke()
        except Exception as exc:
            if kwargs.get("response_format") is not None and is_unsupported_response_format_error(exc):
                log.warning(
                    "LightRAG 关键词/结构化 response_format 不可用，回退普通调用: %s",
                    exc,
                )
                kwargs.pop("response_format", None)
                return await _invoke()
            raise

    # 选择优先级：
    # 1) LIGHTRAG_EMBED_* 环境变量
    # 2) modelCfg.json 中 model_type=embedding 且同档位
    # 3) 回退到当前 chat 模型
    embedding_entry = select_embedding_entry(str(entry.get("model_level", "")).strip())
    embed_cfg = resolve_embedding_params(entry, embedding_entry)
    embedding_model = str(embed_cfg["model"])
    embedding_api = str(embed_cfg["api"])
    embedding_key = str(embed_cfg["key"])
    embedding_dim = int(embed_cfg["dim"])
    max_token_size = int(embed_cfg["max_tokens"])
    log.info(
        "LightRAG embedding 参数确定完成, model=%s, api=%s, dim=%s, max_tokens=%s",
        embedding_model,
        embedding_api,
        embedding_dim,
        max_token_size,
    )

    from lightrag.utils import wrap_embedding_func_with_attrs
    import numpy as np

    def _infer_embedding_dim(result: Any) -> int:
        """从 embedding 结果推断单向量维度。"""
        try:
            arr = np.asarray(result)
            if arr.ndim == 1:
                return int(arr.shape[0]) if arr.shape and arr.shape[0] > 0 else -1
            if arr.ndim >= 2:
                return int(arr.shape[-1]) if arr.shape[-1] > 0 else -1
            return -1
        except Exception:
            return -1

    wrapper_ref: dict[str, Any] = {"obj": None}

    @wrap_embedding_func_with_attrs(
        embedding_dim=embedding_dim,
        max_token_size=max_token_size,
        model_name=embedding_model,
    )
    async def _embedding_func(texts: list[str]) -> Any:
        trace_id = "emb-" + uuid.uuid4().hex[:8]
        text_count = len(texts or [])
        preview = (texts[0][:120] if texts and texts[0] else "") if text_count > 0 else ""
        use_single_string_input = text_count == 1
        input_payload: Any = texts[0] if use_single_string_input else texts
        expected_endpoint = embedding_api.rstrip("/") + "/embeddings"
        log.info(
            "LightRAG Embedding 调用开始, trace_id=%s, base_url=%s, model=%s, text_count=%s, input_mode=%s, first_text_preview=%s",
            trace_id,
            embedding_api,
            embedding_model,
            text_count,
            "string" if use_single_string_input else "list",
            preview,
        )
        log.info(
            "LightRAG Embedding 预期请求地址, trace_id=%s, endpoint=%s",
            trace_id,
            expected_endpoint,
        )
        try:
            embed_http_timeout = float(
                os.getenv(
                    "LIGHTRAG_EMBED_HTTP_TIMEOUT",
                    os.getenv("EMBEDDING_TIMEOUT", "180"),
                )
                or "180"
            )
            embed_http_timeout = max(30.0, embed_http_timeout)
            result = await openai_embed.func(
                input_payload,
                model=embedding_model,
                api_key=embedding_key,
                base_url=embedding_api,
                client_configs={"timeout": embed_http_timeout},
            )
            arr = np.asarray(result)
            actual_dim = _infer_embedding_dim(result)
            vector_count = int(arr.shape[0]) if arr.ndim >= 2 else (1 if arr.ndim == 1 and arr.size > 0 else -1)
            first_vector_dim = actual_dim
            wrapper_obj = wrapper_ref.get("obj")
            if wrapper_obj is not None and actual_dim > 0 and int(getattr(wrapper_obj, "embedding_dim", -1)) != actual_dim:
                old_dim = int(getattr(wrapper_obj, "embedding_dim", -1))
                setattr(wrapper_obj, "embedding_dim", actual_dim)
                log.warning(
                    "LightRAG Embedding 维度自动纠偏, model=%s, configured_dim=%s, actual_dim=%s",
                    embedding_model,
                    old_dim,
                    actual_dim,
                )
            log.info(
                "LightRAG Embedding 调用成功, trace_id=%s, base_url=%s, model=%s, text_count=%s, vector_count=%s, first_vector_dim=%s",
                trace_id,
                embedding_api,
                embedding_model,
                text_count,
                vector_count,
                first_vector_dim,
            )
            return result
        except Exception as exc:
            log.exception(
                "LightRAG Embedding 调用失败, trace_id=%s, base_url=%s, model=%s, text_count=%s, error_type=%s, error=%s",
                trace_id,
                embedding_api,
                embedding_model,
                text_count,
                exc.__class__.__name__,
                str(exc),
            )
            raise

    wrapper_ref["obj"] = _embedding_func
    return _llm_model_func, _embedding_func
