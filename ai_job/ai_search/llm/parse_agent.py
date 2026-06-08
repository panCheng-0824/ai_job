"""正文 → 结构化字段（LLM 或规则降级）。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_search.llm.client import invoke_text, parse_json_from_llm
from ai_search.llm.prompts import PARSE_PROMPT
from ai_search.step_log import log_substep, log_warn

if TYPE_CHECKING:
    from ai_search.models import CrawlTask, PageRecord

logger = logging.getLogger(__name__)


def parse_page_fields(
    body: str,
    prompt: str,
    *,
    model_level: str = "",
    page_index: int = 1,
    parent_step: int | None = None,
) -> dict:
    """对单页正文做 LLM 字段解析。"""
    if not prompt or not body:
        return {"raw_body_preview": (body or "")[:500]}
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            f"parse-{page_index}",
            "LLM 解析页面字段",
            body_len=len(body),
            prompt_preview=(prompt[:60] + "…") if len(prompt) > 60 else prompt,
        )
    text = invoke_text(
        PARSE_PROMPT.format(prompt=prompt, body=body[:6000]),
        model_level=model_level,
        purpose="parse",
    )
    parsed = parse_json_from_llm(text)
    if isinstance(parsed, dict):
        if parent_step is not None:
            log_substep(
                logger,
                parent_step,
                f"parse-{page_index}-ok",
                "字段解析成功",
                field_keys=list(parsed.keys()),
            )
        return parsed
    if isinstance(parsed, list) and parsed:
        if parent_step is not None:
            log_substep(
                logger,
                parent_step,
                f"parse-{page_index}-ok",
                "字段解析为列表",
                item_count=len(parsed),
            )
        return {"items": parsed}
    log_warn(
        logger,
        "LLM",
        "字段解析降级",
        page_index=page_index,
        llm_note=text or "llm_unavailable",
    )
    return {"raw_body_preview": body[:500], "llm_note": text or "llm_unavailable"}


def enrich_pages_with_llm(
    pages: list[PageRecord],
    task: CrawlTask,
    *,
    parent_step: int | None = None,
) -> tuple[list[PageRecord], bool]:
    """为每页补充 LLM 解析字段；返回 (pages, llm_used)。"""
    if not task.prompt:
        if parent_step is not None:
            log_substep(logger, parent_step, 1, "无 prompt，跳过 LLM 解析")
        return pages, False

    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            1,
            "开始逐页 LLM 解析",
            page_count=len(pages),
        )

    llm_used = False
    for idx, page in enumerate(pages, start=1):
        merged = dict(page.fields) if page.fields else {}
        extra = parse_page_fields(
            page.body,
            task.prompt,
            model_level=task.model_level,
            page_index=idx,
            parent_step=parent_step,
        )
        if extra and "llm_unavailable" not in str(extra.get("llm_note", "")):
            llm_used = True
        merged.update(extra)
        page.fields = merged

    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            2,
            "逐页 LLM 解析结束",
            llm_used=llm_used,
            page_count=len(pages),
        )
    return pages, llm_used
