"""运行时配置辅助工具。

本模块集中处理：
1) 读取 ``runtime_config.json``；
2) 解析环境变量/配置中的布尔、整数、浮点值；
3) 统一执行“环境变量 > 配置文件 > 默认值”的优先级规则。

将该逻辑集中管理，可避免在 ``pipeline_llm.py`` 与 ``user_session.py`` 中重复实现。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = ROOT / "config" / "runtime_config.json"


def load_runtime_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """读取运行时配置 JSON；任意异常时返回空字典。"""
    target = path or RUNTIME_CONFIG_PATH
    if not target.is_file():
        return {}
    try:
        with target.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def parse_bool(value: Any) -> Optional[bool]:
    """解析布尔值或常见布尔字符串字面量。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"0", "false", "off", "no"}:
            return False
    return None


def parse_float(value: Any, default: float, *, min_value: Optional[float] = None) -> float:
    """解析浮点值；失败回退默认值，并可设置下界。"""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None and parsed < min_value:
        return default
    return parsed


def parse_int(value: Any, default: int, *, min_value: Optional[int] = None) -> int:
    """解析整数值；失败回退默认值，并可设置下界。"""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None and parsed < min_value:
        return default
    return parsed


def resolve_bool_setting(
    *,
    env_key: str,
    config_key: str,
    default: bool,
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """按“环境变量 > 配置文件 > 默认值”解析布尔配置。"""
    env_value = parse_bool(os.getenv(env_key))
    if env_value is not None:
        return env_value
    cfg = config or load_runtime_config()
    cfg_value = parse_bool(cfg.get(config_key))
    if cfg_value is not None:
        return cfg_value
    return default


def resolve_float_setting(
    *,
    env_key: str,
    config_key: str,
    default: float,
    min_value: Optional[float] = None,
    config: Optional[Dict[str, Any]] = None,
) -> float:
    """按“环境变量 > 配置文件 > 默认值”解析浮点配置。"""
    env_raw = os.getenv(env_key)
    if env_raw is not None:
        return parse_float(env_raw, default, min_value=min_value)
    cfg = config or load_runtime_config()
    return parse_float(cfg.get(config_key), default, min_value=min_value)


def resolve_int_setting(
    *,
    env_key: str,
    config_key: str,
    default: int,
    min_value: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
) -> int:
    """按“环境变量 > 配置文件 > 默认值”解析整型配置。"""
    env_raw = os.getenv(env_key)
    if env_raw is not None:
        return parse_int(env_raw, default, min_value=min_value)
    cfg = config or load_runtime_config()
    return parse_int(cfg.get(config_key), default, min_value=min_value)
