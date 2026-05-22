"""前端 recommendation 块：match_status / recommended_jobs / no_match_detail。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def infer_kb_source(data: Dict[str, Any]) -> str:
    """推断 lightrag / greprag / unknown。"""
    ds = str(data.get("data_source") or "")
    if ds.startswith("lightrag"):
        return "lightrag"
    if ds.startswith("greprag"):
        return "greprag"
    mode = str((data.get("rag") or {}).get("mode") or "")
    if mode.startswith("lightrag"):
        return "lightrag"
    if mode.startswith("greprag"):
        return "greprag"
    return "unknown"


def no_match_detail(data: Dict[str, Any]) -> Dict[str, Any]:
    """无检索素材或失败时的说明块（对齐 StudentView）。"""
    rag = data.get("rag") or {}
    hint = str(rag.get("hint") or "").strip()
    err = str(rag.get("error") or "").strip()
    causes = [x for x in (err, hint) if x] or ["未返回知识库检索素材。"]
    return {
        "title": "暂无检索结果",
        "causes": causes,
        "suggestions": [
            "尝试换成更具体的岗位名、技能或城市关键词。",
            "确认知识库已同步岗位文档后重试。",
        ],
    }


def build_recommendation_retrieval_only(data: Dict[str, Any]) -> Dict[str, Any]:
    """有检索正文、尚未/无需 LLM 填岗位列表。"""
    rag = data.get("rag") or {}
    kb_source = infer_kb_source(data)
    return {
        "match_status": "retrieval_only",
        "kb_source": kb_source,
        "recommended_jobs": [],
        "no_match_detail": None,
        "notes": [
            str(
                rag.get("hint")
                or "已返回知识库检索素材（rag.retrieval_context），"
                "请使用业务侧自定义模型结合 query 分析。"
            )
        ],
    }


def build_recommendation_no_match(
    data: Dict[str, Any],
    *,
    causes: List[str],
    suggestions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """明确无推荐（含 LLM 判定或解析失败）。"""
    return {
        "match_status": "no_match",
        "kb_source": infer_kb_source(data),
        "recommended_jobs": [],
        "no_match_detail": {
            "title": "暂无推荐",
            "causes": causes,
            "suggestions": suggestions
            or [
                "可调整诉求关键词后重试。",
                "确认知识库素材是否包含目标岗位。",
            ],
        },
        "notes": None,
    }


def build_recommendation_matched(
    data: Dict[str, Any], recommended_jobs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """LLM 已产出可展示岗位列表。"""
    return {
        "match_status": "matched",
        "kb_source": infer_kb_source(data),
        "recommended_jobs": recommended_jobs,
        "no_match_detail": None,
        "notes": None,
    }


def decorate_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    附加 recommendation 字段（不修改 jobs / rag 正文）。

    - 有 retrieval_context 且 enabled → retrieval_only
    - 否则 → no_match + no_match_detail
    """
    rag = data.get("rag") or {}
    retrieval_text = str(rag.get("retrieval_context") or "").strip()
    if rag.get("enabled") and retrieval_text:
        rec = build_recommendation_retrieval_only(data)
    else:
        rec = build_recommendation_no_match(data, causes=no_match_detail(data)["causes"])
    return {**data, "recommendation": rec}
