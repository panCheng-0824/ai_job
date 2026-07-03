"""解析与规范化大模型返回的 recom JSON。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


class RecomJsonParseError(ValueError):
    """岗位推荐 LLM 输出 JSON 无法解析。"""

    def __init__(self, message: str, *, raw_preview: str = "") -> None:
        super().__init__(message)
        self.raw_preview = raw_preview


def _strip_markdown_fence(text: str) -> str:
    raw = (text or "").strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.I)
    return match.group(1).strip() if match else raw


def _slice_outer_object(text: str) -> str:
    raw = (text or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        return raw[start : end + 1]
    return raw


def _repair_json_text(text: str) -> str:
    """修复模型输出中常见的非标准 JSON（不保证万能）。"""
    s = text
    s = s.replace("\ufeff", "")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    # 去掉 // 与 /* */ 注释（仅当不在字符串内时较安全，此处做简单启发）
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*[\s\S]*?\*/", "", s)
    # 尾逗号
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s.strip()


def _json_candidates(text: str) -> List[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    seen: set[str] = set()
    out: List[str] = []

    def add(candidate: str) -> None:
        c = (candidate or "").strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)

    add(_strip_markdown_fence(raw))
    add(_slice_outer_object(raw))
    add(raw)
    match = re.search(r"(\{[\s\S]*\})", raw)
    if match:
        add(match.group(1))
    return out


def _try_load_object(text: str) -> Optional[Dict[str, Any]]:
    for variant in (text, _repair_json_text(text)):
        try:
            parsed = json.loads(variant)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_recom_json(text: str) -> Dict[str, Any]:
    """
    解析模型输出为 recom JSON 对象。

    依次尝试：去 markdown 围栏、截取最外层 `{}`、修复尾逗号/智能引号后再 ``json.loads``。
    全部失败时抛出 ``RecomJsonParseError``。
    """
    candidates = _json_candidates(text)
    if not candidates:
        raise RecomJsonParseError("模型输出为空", raw_preview="")

    last_err = ""
    for candidate in candidates:
        parsed = _try_load_object(candidate)
        if parsed is not None:
            return normalize_recom_payload(parsed)
        try:
            json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_err = str(exc)

    preview = (text or "").strip()
    if len(preview) > 400:
        preview = preview[:400] + "…"
    raise RecomJsonParseError(
        f"JSON 解析失败: {last_err or '无法识别 JSON 对象'}",
        raw_preview=preview,
    )


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
