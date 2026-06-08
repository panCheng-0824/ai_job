"""统一 STEP 运行日志（风格对齐 online_search）。"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

_current_main_step: ContextVar[int] = ContextVar("ai_search_main_step", default=0)


def reset_steps() -> None:
    """新任务开始前重置步骤计数。"""
    _current_main_step.set(0)


def _format_fields(**fields: Any) -> str:
    if not fields:
        return ""
    return ", ".join(f"{key}={value}" for key, value in fields.items())


def log_init(logger: logging.Logger, message: str, **fields: Any) -> None:
    suffix = _format_fields(**fields)
    if suffix:
        logger.info("[INIT] %s: %s", message, suffix)
    else:
        logger.info("[INIT] %s", message)


def log_step(logger: logging.Logger, message: str, **fields: Any) -> int:
    """记录主流程步骤，返回步骤编号。"""
    step_no = _current_main_step.get() + 1
    _current_main_step.set(step_no)
    suffix = _format_fields(**fields)
    if suffix:
        logger.info("[STEP %s] %s: %s", step_no, message, suffix)
    else:
        logger.info("[STEP %s] %s", step_no, message)
    return step_no


def log_substep(
    logger: logging.Logger,
    parent: int,
    sub: int | str,
    message: str,
    **fields: Any,
) -> None:
    """记录子步骤，例如 STEP 3.1。"""
    suffix = _format_fields(**fields)
    label = f"{parent}.{sub}"
    if suffix:
        logger.info("[STEP %s] %s: %s", label, message, suffix)
    else:
        logger.info("[STEP %s] %s", label, message)


def log_phase(logger: logging.Logger, phase: str, message: str, **fields: Any) -> None:
    """子模块固定阶段标签，例如 [BROWSER] / [SCRAPY]。"""
    suffix = _format_fields(**fields)
    if suffix:
        logger.info("[%s] %s: %s", phase, message, suffix)
    else:
        logger.info("[%s] %s", phase, message)


def log_done(logger: logging.Logger, message: str, **fields: Any) -> None:
    suffix = _format_fields(**fields)
    if suffix:
        logger.info("[DONE] %s: %s", message, suffix)
    else:
        logger.info("[DONE] %s", message)


def log_warn(logger: logging.Logger, tag: str, message: str, **fields: Any) -> None:
    suffix = _format_fields(**fields)
    if suffix:
        logger.warning("[%s] %s: %s", tag, message, suffix)
    else:
        logger.warning("[%s] %s", tag, message)


def get_current_step() -> int:
    """返回当前主流程步骤编号。"""
    return _current_main_step.get()


def log_error(logger: logging.Logger, message: str, **fields: Any) -> None:
    suffix = _format_fields(**fields)
    if suffix:
        logger.error("[STEP ERROR] %s: %s", message, suffix)
    else:
        logger.error("[STEP ERROR] %s", message)
