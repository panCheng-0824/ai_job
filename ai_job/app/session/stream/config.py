"""
SSE 流配置解析 — 来自 usermodel.json 的 stream_handler / stream_options。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

HANDLER_OPENAI_DIRECT = "openai_direct"
HANDLER_ADVERSARIAL_HARNESS = "adversarial_harness"

KNOWN_HANDLERS = frozenset({HANDLER_OPENAI_DIRECT, HANDLER_ADVERSARIAL_HARNESS})


def stream_options_from_user_model(user_model: Dict[str, Any]) -> Dict[str, Any]:
    """读取当前 user_model 条目的 stream_options。"""
    raw = user_model.get("stream_options") or {}
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def coerce_adversarial_rounds(merged: Dict[str, Any]) -> int:
    """对抗轮次：默认 3，与 cap 取 min，限制 1～10。"""
    raw = merged.get("adversarial_max_rounds")
    try:
        base = int(raw) if raw is not None else 3
    except (TypeError, ValueError):
        base = 3
    base = max(1, min(base, 10))
    cap = merged.get("adversarial_max_rounds_cap")
    if cap is not None:
        try:
            c = max(1, min(int(cap), 10))
            base = min(base, c)
        except (TypeError, ValueError):
            pass
    return base


def resolve_adversarial_max_rounds_from_user_model(user_model: Dict[str, Any]) -> int:
    """供非流式 harness 与管线共用。"""
    return coerce_adversarial_rounds(stream_options_from_user_model(user_model))


def finalize_runtime_fields(
    merged: Dict[str, Any],
    *,
    use_role_pipeline: bool,
) -> Dict[str, Any]:
    """合并 temperature、对抗轮次等到运行时 dict。"""
    try:
        temperature = float(merged.get("temperature", 0.0))
    except (TypeError, ValueError):
        temperature = 0.0
    return {
        "temperature": temperature,
        "adversarial_max_rounds": coerce_adversarial_rounds(merged),
        "use_role_pipeline": use_role_pipeline,
    }


def resolve_stream_handler_and_options(
    user_model: Dict[str, Any],
    *,
    use_adversarial_harness: bool,
    use_role_pipeline: bool,
) -> Tuple[str, Dict[str, Any]]:
    """
    解析本请求的 stream handler 与运行时选项。

    对抗模式仅由页面开关触发，忽略 usermodel 中误配的 adversarial handler。
    """
    if use_adversarial_harness:
        merged = stream_options_from_user_model(user_model)
        return HANDLER_ADVERSARIAL_HARNESS, finalize_runtime_fields(
            merged, use_role_pipeline=use_role_pipeline
        )

    usercode = str(user_model.get("usercode", "")).strip()
    explicit = str(user_model.get("stream_handler") or "").strip()
    if explicit == HANDLER_ADVERSARIAL_HARNESS:
        explicit = ""

    handler_id = explicit or HANDLER_OPENAI_DIRECT
    if handler_id not in KNOWN_HANDLERS:
        logger.warning(
            "usercode=%s 配置的 stream_handler=%s 未实现，回退到 %s",
            usercode,
            handler_id,
            HANDLER_OPENAI_DIRECT,
        )
        handler_id = HANDLER_OPENAI_DIRECT

    merged = stream_options_from_user_model(user_model)
    return handler_id, finalize_runtime_fields(merged, use_role_pipeline=use_role_pipeline)
