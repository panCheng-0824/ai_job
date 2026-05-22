"""解析与规范化大模型返回的 recom JSON。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def parse_recom_json(text: str) -> Dict[str, Any]:
    """解析模型输出，容忍 ```json 代码块。"""
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fenced:
        raw = fenced.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("模型输出不是 JSON 对象")
    return normalize_recom_payload(parsed)


def normalize_recom_payload(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """统一 recomList 为对象列表。"""
    out = dict(parsed)
    raw_list = out.get("recomList")
    if raw_list is None:
        raw_list = out.get("recomlist")
    if not isinstance(raw_list, list):
        raw_list = []
    out["recomList"] = [x for x in raw_list if isinstance(x, dict)]
    return out


def coerce_score(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def is_recommend_yes(value: Any) -> bool:
    return str(value or "").strip().lower() in ("yes", "on", "y", "true", "1")


def recom_list_from_parsed(parsed: Dict[str, Any]) -> List[Any]:
    raw = parsed.get("recomList") or parsed.get("recomlist") or []
    return raw if isinstance(raw, list) else []
