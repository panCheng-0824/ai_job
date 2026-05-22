"""从 modelCfg.json 读取模型配置，得到带类型标注的列表。"""

import json  # 解析 JSON 文件
from pathlib import Path  # 跨平台路径，用于定位配置文件
from typing import Any, List, Optional, TypedDict, cast  # 类型注解与 TypedDict 结构


class ModelEntry(TypedDict):
    """单条模型配置在 JSON 中的字段形状（静态类型检查用）。"""

    model_type: str  # 模型类型：chat / embedding / tts / asr
    model_level: str  # 档位：如 low / mid / high
    model_provider: str  # 提供方标识，如 openai
    model_name: str  # 模型名称，传给 Chat API
    model_api: str  # OpenAI 兼容服务的 base URL
    model_key: str  # API Key


# 每条记录必须出现的键，用于校验 JSON
_KEYS = ("model_level", "model_provider", "model_name", "model_api", "model_key")


def load_model_list(cfg_path: Optional[Path] = None) -> List[ModelEntry]:
    """读取配置文件，返回 ModelEntry 列表；cfg_path 缺省时用本文件同目录下的 modelCfg.json。"""
    path = cfg_path or Path(__file__).resolve().parent / "config" / "modelCfg.json"  # 默认配置文件路径
    with path.open(encoding="utf-8") as f:  # 按 UTF-8 打开，避免中文路径/内容问题
        raw: Any = json.load(f)  # 先解析为任意结构，下面再校验
    if not isinstance(raw, list):  # 约定根类型为数组
        raise ValueError("modelCfg must be a JSON array")
    model_list: List[ModelEntry] = []  # 累积校验通过后的条目
    for item in raw:  # 遍历数组中的每一项
        if not isinstance(item, dict):  # 每条必须是 JSON 对象
            raise ValueError("each model entry must be an object")
        missing = [k for k in _KEYS if k not in item]  # 收集缺失字段
        if missing:  # 缺任一必填键则报错
            raise KeyError(f"missing keys: {missing}")
        # 兼容旧结构：若未提供 model_type，默认视为 chat。
        if "model_type" not in item:
            item["model_type"] = "chat"
        model_list.append(cast(ModelEntry, item))  # 运行时已是 dict，cast 满足类型检查
    return model_list  # 返回完整模型列表
