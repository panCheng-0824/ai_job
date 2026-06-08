"""自然语言 → CSS 选择器（带简单校验）。"""

from __future__ import annotations

import logging

from ai_search.html_utils import trim_html_for_llm
from ai_search.llm.client import invoke_text
from ai_search.llm.prompts import SELECTOR_PROMPT
from ai_search.step_log import log_substep, log_warn

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _validate_selector(selector: str) -> bool:
    s = (selector or "").strip()
    if not s or s.upper() == "NONE":
        return False
    if len(s) > 200:
        return False
    return True


def suggest_link_selector(
    html: str,
    prompt: str,
    *,
    model_level: str = "",
    parent_step: int | None = None,
    sub_step: int | str = 1,
) -> str:
    """根据 HTML 与用户需求建议列表链接 CSS 选择器。"""
    page_text = trim_html_for_llm(html, max_chars=4000)
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            sub_step,
            "LLM 生成链接选择器",
            html_chars=len(html),
            prompt_preview=(prompt[:60] + "…") if len(prompt) > 60 else prompt,
        )
    for attempt in range(1, MAX_RETRIES + 1):
        text = invoke_text(
            SELECTOR_PROMPT.format(prompt=prompt or "提取列表中的链接", page_text=page_text),
            model_level=model_level,
            purpose="selector",
        )
        if not text:
            log_warn(logger, "LLM", "选择器生成无响应", attempt=attempt)
            break
        selector = text.splitlines()[0].strip().strip("`\"'")
        if _validate_selector(selector):
            if parent_step is not None:
                log_substep(
                    logger,
                    parent_step,
                    f"{sub_step}-ok",
                    "选择器生成成功",
                    attempt=attempt,
                    selector=selector,
                )
            return selector
        if parent_step is not None:
            log_substep(
                logger,
                parent_step,
                f"{sub_step}-retry",
                "选择器无效，准备重试",
                attempt=attempt,
                raw_preview=text[:80],
            )
    return ""
