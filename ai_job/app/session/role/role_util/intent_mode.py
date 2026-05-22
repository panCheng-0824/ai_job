"""
角色流水线 — 从用户模型读取 ``stream_options`` 中的意图模式覆盖。
"""

from __future__ import annotations

from typing import Tuple


def resolve_stream_option_mode(
    merged_user: dict,
    *,
    option_key: str = "intent_mode",
    allowed: Tuple[str, ...] = ("auto",),
    default: str = "auto",
) -> str:
    """
    读取 ``stream_options.<option_key>`` 或顶层 ``<option_key>``。

    参数
    ----
    allowed:
        合法取值元组；不在其中则回退 ``default``。
    """
    allowed_set = set(allowed)
    fallback = default if default in allowed_set else (allowed[0] if allowed else default)

    opts = merged_user.get("stream_options")
    if isinstance(opts, dict):
        mode = str(opts.get(option_key, "")).strip().lower()
        if mode in allowed_set:
            return mode
    mode = str(merged_user.get(option_key, "")).strip().lower()
    if mode in allowed_set:
        return mode
    return fallback
