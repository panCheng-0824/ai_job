"""LightRAG 统一链路日志工具。"""

from __future__ import annotations

import logging
import uuid


def new_op_id(prefix: str) -> str:
    """生成统一格式的操作 ID，便于跨函数关联日志。"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def step(log: logging.Logger, op_id: str, step_no: int, message: str, *args: object) -> None:
    """输出带步骤号的链路日志。"""
    log.info("[op=%s][step=%02d] " + message, op_id, step_no, *args)
