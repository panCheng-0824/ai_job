"""
角色流水线 — 模型输出解析（ROLE001 / ROLE004 等共用）。
"""

from __future__ import annotations

import json
import re
from typing import List, Tuple


def strip_markdown_json_fence(text: str) -> str:
    """去掉模型输出外层可能出现的 Markdown JSON 代码围栏。"""
    raw = (text or "").strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    return match.group(1).strip() if match else raw


def parse_plan_json(text: str) -> List[str]:
    """解析 planner 节点返回的步骤列表；失败时退化为单步原文。"""
    raw = strip_markdown_json_fence(text)
    try:
        data = json.loads(raw)
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            steps = [x.strip() for x in data if x.strip()]
            return steps if steps else [raw]
    except json.JSONDecodeError:
        pass
    return [raw] if raw else ["（规划为空）"]


def parse_structured_blob(text: str) -> Tuple[str, str]:
    """解析 structured_return 节点的 JSON；返回 (pretty_json, summary)。"""
    raw = strip_markdown_json_fence(text)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            summary = str(data.get("summary") or data.get("回答摘要") or "").strip()
            pretty = json.dumps(data, ensure_ascii=False, indent=2)
            return pretty, summary
    except json.JSONDecodeError:
        pass
    return raw, ""
