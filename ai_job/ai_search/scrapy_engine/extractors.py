"""页面正文与字段提取（ai_search 主实现，online_search 可从此导入）。"""

from __future__ import annotations

import logging
from typing import Any

from bs4 import BeautifulSoup
from readability import Document

from .settings import MAX_BODY_CHARS, MIN_BODY_LEN

logger = logging.getLogger(__name__)


def extract_body_from_html(html: str, *, max_chars: int = MAX_BODY_CHARS) -> str:
    """从 HTML 字符串提取正文。"""
    body = ""
    try:
        doc = Document(html or "")
        summary = doc.summary(html_partial=True)
        body = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
    except Exception as exc:
        logger.info("[EXTRACT] readability 提取失败，将回退段落拼接: %s", exc)

    if len(body) < MIN_BODY_LEN:
        soup = BeautifulSoup(html or "", "html.parser")
        parts = [
            p.get_text(" ", strip=True)
            for p in soup.select("article p, main p, p")
            if p.get_text(strip=True)
        ]
        body = " ".join(parts).strip() or soup.get_text(" ", strip=True)

    return (body or "")[:max_chars]


def extract_body_text(response, logger_obj=None) -> str:
    """Scrapy Response 正文提取。"""
    log = logger_obj or logger
    try:
        text = extract_body_from_html(response.text)
        if text:
            return text
    except Exception as exc:
        log.info("[extract] 正文提取异常: %s", exc)
    fallback = " ".join(response.css("article p::text, p::text").getall()).strip()
    return fallback[:MAX_BODY_CHARS]


def extract_fields_with_selectors(
    html: str,
    selectors: dict[str, str],
) -> dict[str, Any]:
    """按 CSS 选择器提取字段。"""
    soup = BeautifulSoup(html or "", "html.parser")
    out: dict[str, Any] = {}
    for name, css in selectors.items():
        if not css:
            continue
        nodes = soup.select(css)
        if not nodes:
            out[name] = ""
            continue
        if len(nodes) == 1:
            out[name] = nodes[0].get_text(" ", strip=True)
        else:
            out[name] = [n.get_text(" ", strip=True) for n in nodes[:50]]
    return out
