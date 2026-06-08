"""采集模式建议（auto 模式）。"""

from __future__ import annotations

import logging

from ai_search.llm.client import invoke_text
from ai_search.llm.prompts import MODE_ADVISOR_PROMPT
from ai_search.models import CrawlMode, CrawlTask
from ai_search.step_log import log_substep, log_warn

logger = logging.getLogger(__name__)


def advise_mode(
    task: CrawlTask,
    *,
    has_session: bool,
    parent_step: int | None = None,
) -> CrawlMode:
    """根据任务与 LLM 建议返回模式；失败则用规则。"""
    if task.require_login and not has_session:
        if parent_step is not None:
            log_substep(
                logger,
                parent_step,
                "rule",
                "规则决策：需登录且无会话 → hybrid",
            )
        return CrawlMode.HYBRID
    if task.require_login and has_session:
        if parent_step is not None:
            log_substep(
                logger,
                parent_step,
                "rule",
                "规则决策：需登录且已有会话 → scrapy",
            )
        return CrawlMode.SCRAPY

    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            "llm",
            "调用 LLM 建议采集模式",
            url=task.url,
            has_session=has_session,
        )
    text = invoke_text(
        MODE_ADVISOR_PROMPT.format(
            url=task.url,
            require_login=task.require_login,
            has_session=has_session,
            prompt=task.prompt,
        ),
        model_level=task.model_level,
        purpose="mode_advisor",
    )
    if text:
        word = text.strip().split()[0].lower()
        for mode in CrawlMode:
            if mode.value == word:
                if parent_step is not None:
                    log_substep(
                        logger,
                        parent_step,
                        "llm-ok",
                        "LLM 模式建议",
                        mode=mode.value,
                        raw=text[:40],
                    )
                return mode

    if parent_step is not None:
        log_substep(logger, parent_step, "fallback", "LLM 无有效建议，默认 scrapy")
    else:
        log_warn(logger, "LLM", "模式建议失败，默认 scrapy")
    return CrawlMode.SCRAPY
