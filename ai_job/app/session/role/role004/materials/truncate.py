"""ROLE004 — 文本截断与长度上限配置。"""

from __future__ import annotations

import os

_TRUNC_SUFFIX = "…（内容过长已截断，请结合已有信息生成）"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(500, int(raw))
    except ValueError:
        return default


MAX_CARD_BODY_CHARS = _env_int("ROLE004_MAX_CARD_BODY_CHARS", 3500)
MAX_JOB_DESC_CHARS = _env_int("ROLE004_MAX_JOB_DESC_CHARS", 1800)
MAX_MATERIALS_BLOCK_CHARS = _env_int("ROLE004_MAX_MATERIALS_BLOCK_CHARS", 10000)
MAX_STUDENT_CONTEXT_CHARS = _env_int("ROLE004_MAX_STUDENT_CONTEXT_CHARS", 3500)


def truncate_text(text: str, max_chars: int, *, suffix: str = _TRUNC_SUFFIX) -> str:
    """截断过长文本，避免简历生成请求超时。"""
    raw = (text or "").strip()
    if max_chars <= 0 or len(raw) <= max_chars:
        return raw
    keep = max(200, max_chars - len(suffix))
    return raw[:keep] + suffix
