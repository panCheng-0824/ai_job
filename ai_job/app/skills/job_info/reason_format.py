"""岗位推荐理由结构化解析（供 API / 前端展示）。"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# 与 llm_prompt 中约定的四段标题一致
SECTION_SPECS: List[tuple[str, str, tuple[str, ...]]] = [
    ("conclusion", "匹配结论", ("【匹配结论】", "①匹配结论：", "①匹配结论:")),
    ("score_basis", "评分依据", ("【评分依据】", "②评分依据：", "②评分依据:")),
    ("evidence", "素材依据", ("【素材依据】", "③素材依据：", "③素材依据:")),
    ("gap", "差异提示", ("【差异提示】", "④差异提示：", "④差异提示:")),
]

MIN_REASON_CHARS = 300


def parse_match_reason_sections(text: str) -> List[Dict[str, str]]:
    """将 reason 文本解析为带 title/body 的分段列表；无法识别时整段作为单块。"""
    raw = (text or "").strip()
    if not raw:
        return []

    markers: List[tuple[int, str, str, str]] = []
    for key, title, prefixes in SECTION_SPECS:
        for prefix in prefixes:
            idx = raw.find(prefix)
            if idx >= 0:
                markers.append((idx, key, title, prefix))
                break

    if not markers:
        return [{"key": "full", "title": "推荐理由", "body": raw}]

    markers.sort(key=lambda x: x[0])
    out: List[Dict[str, str]] = []
    for i, (_pos, key, title, prefix) in enumerate(markers):
        start = raw.find(prefix) + len(prefix)
        end = markers[i + 1][0] if i + 1 < len(markers) else len(raw)
        body = raw[start:end].strip().strip("；;")
        if body:
            out.append({"key": key, "title": title, "body": body})
    return out


def reason_char_count(text: str) -> int:
    return len(re.sub(r"\s+", "", (text or "")))


def enrich_recom_reason(item: Dict[str, Any]) -> Dict[str, Any]:
    """为 recomList 单项附加 match_reason_sections、reason_char_count。"""
    reason = str(item.get("reason") or "").strip()
    sections = parse_match_reason_sections(reason)
    out = dict(item)
    out["reason"] = reason
    out["match_reason_sections"] = sections
    out["reason_char_count"] = reason_char_count(reason)
    return out
