"""
ROLE005 — 大纲行业两阶段分类 Agent。

先从 Redis ``top_category`` 桶识别一级行业，再按一级 id 读取二级桶，绑定最终二级 category_id。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.session.role.role005.agents._llm import invoke_llm_json_object
from app.session.role.role005.domain.models import InterviewPlan, PlanIndustryClassification
from app.session.role.role005.infra.industry_category_redis import (
    fetch_level2_categories,
    fetch_top_categories,
)
from app.session.role.role005.parsing import parse_json_object
from app.session.role.role_util.bindings import GraphBindings


def _format_candidates(items: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for it in items:
        cid = it.get("category_id", "")
        name = it.get("category_name", "")
        desc = (it.get("description") or "")[:200]
        kw = (it.get("intent_keywords") or "")[:120]
        lines.append(f"- id={cid} | 名称={name} | 描述={desc} | 关键词={kw}")
    return "\n".join(lines) if lines else "（无候选）"


def _pick_from_list(
    bindings: GraphBindings,
    *,
    stage: str,
    target_role: str,
    plan: InterviewPlan,
    materials_excerpt: str,
    candidates: List[Dict[str, Any]],
    expect_level: int,
) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None, str]:
    if not candidates:
        return None, None, f"{stage} 无可用行业候选"
    prompt = f"""你是面试大纲行业分类助手。当前为「{stage}」，请从候选列表中选出**最匹配**的一项。

## 规则
1. 仅输出 JSON 对象，不要 Markdown。
2. 字段：
   - category_id（string，必须来自候选 id）
   - category_name（string）
   - confidence（number 0~1）
   - reason（string，1~2 句中文）

## 上下文
- 目标岗位：{target_role}
- 期望层级：level={expect_level}
- 素材摘要：{materials_excerpt[:800] or "（无）"}
- 题目数：{len(plan.questions)}

## 候选（只能选一个）
{_format_candidates(candidates)}

JSON 示例：
{{"category_id":"ind_xxx","category_name":"…","confidence":0.86,"reason":"…"}}
"""
    raw = invoke_llm_json_object(bindings, prompt)
    data, err = parse_json_object(raw)
    if err:
        return None, None, err
    cid = str(data.get("category_id") or "").strip()
    matched = next((c for c in candidates if str(c.get("category_id")) == cid), None)
    if not matched:
        return None, None, f"{stage} 返回的 category_id 不在候选列表中"
    return matched, data, ""


def run_plan_industry_classify_agent(
    bindings: GraphBindings,
    *,
    plan: InterviewPlan,
    target_role: str,
    materials_excerpt: str = "",
) -> Tuple[PlanIndustryClassification | None, str]:
    """
    两阶段行业识别：一级 → 二级。

    返回 (classification, error_message)。
    """
    top_items = fetch_top_categories()
    top, top_llm, err = _pick_from_list(
        bindings,
        stage="一级行业识别",
        target_role=target_role or plan.target_role,
        plan=plan,
        materials_excerpt=materials_excerpt,
        candidates=top_items,
        expect_level=1,
    )
    if err or top is None:
        return None, err or "一级行业识别失败"

    l1_id = str(top.get("category_id") or "").strip()
    l2_items = fetch_level2_categories(l1_id)
    l2, l2_llm, err2 = _pick_from_list(
        bindings,
        stage="二级行业识别",
        target_role=target_role or plan.target_role,
        plan=plan,
        materials_excerpt=materials_excerpt,
        candidates=l2_items,
        expect_level=2,
    )
    if err2 or l2 is None:
        return None, err2 or "二级行业识别失败"

    l2_llm = l2_llm or {}
    top_llm = top_llm or {}
    result = PlanIndustryClassification(
        top_category_id=l1_id,
        top_category_name=str(top.get("category_name") or ""),
        industry_category_id=str(l2.get("category_id") or ""),
        industry_category_name=str(l2.get("category_name") or ""),
        confidence=float(l2_llm.get("confidence") or top_llm.get("confidence") or 0.0),
        reason=str(l2_llm.get("reason") or top_llm.get("reason") or ""),
        source="redis_two_stage_llm",
    )
    return result, ""
