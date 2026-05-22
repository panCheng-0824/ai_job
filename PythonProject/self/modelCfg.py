"""从 modelApiCfg.json 加载模型配置并解析为 model_list。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_CONFIG_FILE = Path(__file__).resolve().parent / "modelApiCfg.json"


@dataclass(frozen=True)
class ModelConfig:
    model_level: str
    model_provider: str
    model_name: str
    model_api: str
    model_key: str


def load_model_list(config_path: Path | None = None) -> list[ModelConfig]:
    path = config_path or _CONFIG_FILE
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(f"配置文件应为 JSON 数组: {path}")
    return [ModelConfig(**entry) for entry in raw]


model_list = load_model_list()
