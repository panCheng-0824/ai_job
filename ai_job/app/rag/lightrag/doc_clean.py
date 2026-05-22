"""LightRAG 写入前可选 LLM 文档清洗。"""

from __future__ import annotations

import asyncio
import logging
import os
import time

from .doc_clean_config import doc_clean_enabled, doc_clean_on_error_fallback, resolve_doc_clean_params
from .runtime import load_light_rag_symbols, select_doc_clean_entry, select_llm_entry

log = logging.getLogger(__name__)


async def llm_clean_documents(texts: list[str], model_level: str, op_id: str) -> list[str]:
    """若启用环境变量，则使用独立配置的聊天模型对每条文本做清洗；否则原样返回。"""
    if not texts:
        return texts
    if not doc_clean_enabled():
        log.info(
            "LightRAG 文档清洗(LLM) 未启用, op_id=%s, 跳过；如需启用请设置 LIGHTRAG_DOC_CLEAN_ENABLED=1",
            op_id,
        )
        return texts

    chat_entry = select_llm_entry(model_level)
    clean_entry = select_doc_clean_entry(model_level)
    cfg = resolve_doc_clean_params(chat_entry, clean_entry)
    model = str(cfg["model"])
    api = str(cfg["api"])
    key = str(cfg["key"])
    max_chars = int(cfg["max_chars"])
    system_prompt = str(cfg["system_prompt"])
    temperature = float(cfg["temperature"])

    if not model or not api or not key:
        log.warning(
            "LightRAG 文档清洗(LLM) 配置不完整, op_id=%s, has_model=%s, has_api=%s, has_key=%s, 将跳过 LLM 清洗",
            op_id,
            bool(model),
            bool(api),
            bool(key),
        )
        return texts

    _, _, funcs = load_light_rag_symbols()
    openai_complete_if_cache, _ = funcs

    max_concurrent = max(1, int(os.getenv("LIGHTRAG_DOC_CLEAN_MAX_ASYNC", "1") or "1"))
    sem = asyncio.Semaphore(max_concurrent)

    log.info(
        "LightRAG 文档清洗(LLM) 开始, op_id=%s, model=%s, base_url=%s, docCount=%s, max_async=%s, max_chars=%s",
        op_id,
        model,
        api,
        len(texts),
        max_concurrent,
        max_chars,
    )

    async def _one(idx: int, raw: str) -> str:
        async with sem:
            if max_chars > 0 and len(raw) > max_chars:
                log.warning(
                    "LightRAG 文档清洗(LLM) 跳过超长文档, op_id=%s, index=%s, len=%s, max_chars=%s",
                    op_id,
                    idx,
                    len(raw),
                    max_chars,
                )
                return raw
            started = time.perf_counter()
            user_prompt = (
                "以下为待清洗文档正文，请按要求输出清洗后的正文：\n\n"
                f"{raw}"
            )
            try:
                out = await openai_complete_if_cache(
                    model,
                    user_prompt,
                    system_prompt=system_prompt,
                    history_messages=[],
                    api_key=key,
                    base_url=api,
                    temperature=temperature,
                )
                cleaned = str(out or "").strip()
                if not cleaned:
                    raise RuntimeError("LLM 返回空内容")
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                log.info(
                    "LightRAG 文档清洗(LLM) 单条成功, op_id=%s, index=%s, in_len=%s, out_len=%s, elapsedMs=%s",
                    op_id,
                    idx,
                    len(raw),
                    len(cleaned),
                    elapsed_ms,
                )
                return cleaned
            except Exception:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                log.exception(
                    "LightRAG 文档清洗(LLM) 单条失败, op_id=%s, index=%s, in_len=%s, elapsedMs=%s, fallback=%s",
                    op_id,
                    idx,
                    len(raw),
                    elapsed_ms,
                    doc_clean_on_error_fallback(),
                )
                if doc_clean_on_error_fallback():
                    return raw
                raise

    results: list[str] = await asyncio.gather(*[_one(i, t) for i, t in enumerate(texts)])
    log.info("LightRAG 文档清洗(LLM) 全部完成, op_id=%s, docCount=%s", op_id, len(results))
    return results
