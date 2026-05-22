"""
JSON Schema + ``ChatOpenAI.with_structured_output``：将管道角色的输出约束为标准 JSON 形态。

- 在 ``role_profiles.json`` 中为某角色设置 ``output_schema_path``（相对项目根的路径），
  指向 JSON Schema 文件（可为 Draft 2020-12 常见写法；``additionalProperties: false`` 利于严格模式）。
- 可选 ``structured_primary_field``：在去噪、压缩等场景下，从对象里取单个字符串字段给下游链路段使用；
  未设置时，结构化结果会 ``json.dumps`` 为可读文本（适合对抗审查、画像补充等多字段结果）。

若本地兼容端点不支持 ``json_schema`` 方法，``role_pipeline`` 会捕获异常并回退为普通文本生成。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from langchain_openai import ChatOpenAI

# 当前目录的上级目录即项目根目录（与配置目录、模式目录同级）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def project_root() -> Path:
    """返回项目根目录路径。"""
    return _PROJECT_ROOT


def load_json_schema(relative_path: str) -> Dict[str, Any]:
    """从项目根目录解析相对路径并加载 JSON Schema（根须为 JSON 对象）。"""
    path = (_PROJECT_ROOT / relative_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"JSON schema file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON schema root must be a JSON object")
    return data


def bind_json_schema(llm: ChatOpenAI, schema: Dict[str, Any]) -> Any:
    """绑定 ``with_structured_output``，使用 OpenAI / 兼容栈的 JSON Schema 模式。"""
    return llm.with_structured_output(schema, method="json_schema")
