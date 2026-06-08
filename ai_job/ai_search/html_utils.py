"""HTML 裁剪与精简，供 LLM 与规则解析使用。"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


def strip_scripts_styles(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return str(soup)


def extract_main_text(html: str, *, max_chars: int = 12000) -> str:
    """优先 readability，失败则段落拼接。"""
    from ai_search.scrapy_engine.extractors import extract_body_from_html

    return extract_body_from_html(html, max_chars=max_chars)


def trim_html_for_llm(html: str, *, max_chars: int = 8000) -> str:
    """去掉脚本样式并截断，控制 token。"""
    cleaned = strip_scripts_styles(html)
    text = BeautifulSoup(cleaned, "html.parser").get_text("\n", strip=True)
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated]"
    if len(cleaned) > max_chars * 2:
        return cleaned[: max_chars * 2]
    return cleaned


def guess_title(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
