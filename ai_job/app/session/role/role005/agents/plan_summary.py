"""
ROLE005 — 面试大纲摘要 Agent。

在 Planner 产出 ``InterviewPlan`` 后，生成题库列表所需的简介、适合人群与面试分类标签。
"""

from __future__ import annotations

from app.session.role.role005.agents._llm import invoke_llm_json_object
from app.session.role.role005.domain.models import InterviewPlan, PlanSummary
from app.session.role.role005.parsing import parse_json_object
from app.session.role.role_util.bindings import GraphBindings


def build_plan_summary_prompt(
    *,
    role_block: str,
    target_role: str,
    plan: InterviewPlan,
    materials_excerpt: str,
) -> str:
    """构造大纲摘要 Prompt（仅输出 JSON）。"""
    q_count = len(plan.questions)
    dim_samples = []
    for q in plan.questions[:6]:
        dim_samples.extend(q.dimensions or [])
    dim_hint = "、".join(list(dict.fromkeys(dim_samples))[:12]) or "（见题目 dimensions）"

    return f"""你是面试大纲编辑。请根据下方「目标岗位」与「面试大纲题目列表」生成**题库展示用摘要**。

## 输出要求

1. 仅输出一个 JSON 对象，不要 Markdown 围栏。
2. 字段：
   - ``introduction``（string）：2～4 句中文，概括本套大纲考查重点与题量（共 {q_count} 题），面向「{target_role}」。
   - ``suitable_audience``（string）：1～2 句，说明适合哪类候选人（经验段、技术栈、求职阶段等）。
   - ``interview_categories``（string[]）：3～6 个**面试分类**标签，覆盖本题集主要模块（如「技术基础」「项目深挖」「系统设计」「沟通表达」「岗位匹配」），勿与单题 id 重复。

## 参考

- 目标岗位：{target_role}
- 题目维度样例：{dim_hint}
- 素材摘要（可选）：{materials_excerpt[:1200] or "（无）"}

──角色约束──
{role_block}

──大纲题目（题面摘要）──
{_format_questions_for_summary(plan)}

JSON 示例：
{{"introduction":"…","suitable_audience":"…","interview_categories":["技术基础","项目深挖"]}}
"""


def _format_questions_for_summary(plan: InterviewPlan) -> str:
    """将题面压缩为多行文本，控制 Prompt 长度。"""
    lines: list[str] = []
    for i, q in enumerate(plan.questions, 1):
        text = (q.text or "").strip().replace("\n", " ")
        if len(text) > 120:
            text = text[:120] + "…"
        dims = "、".join(q.dimensions or [])[:80]
        lines.append(f"{i}. [{q.id}] {text}（维度：{dims or '未标注'}）")
    return "\n".join(lines) if lines else "（无题目）"


def run_plan_summary_agent(
    bindings: GraphBindings,
    *,
    plan: InterviewPlan,
    target_role: str,
    materials_excerpt: str = "",
) -> tuple[PlanSummary | None, str]:
    """
    调用 LLM 生成 ``PlanSummary``。

    返回 (summary, error_message)。
    """
    prompt = build_plan_summary_prompt(
        role_block=bindings.role_block,
        target_role=target_role or plan.target_role,
        plan=plan,
        materials_excerpt=materials_excerpt,
    )
    raw = invoke_llm_json_object(bindings, prompt)
    data, parse_err = parse_json_object(raw)
    if parse_err:
        return None, parse_err
    try:
        summary = PlanSummary.model_validate(data)
    except Exception as exc:
        return None, f"摘要 Schema 校验失败: {exc}"
    if not (summary.introduction or "").strip():
        return None, "摘要缺少 introduction"
    if not summary.interview_categories:
        return None, "摘要缺少 interview_categories"
    return summary, ""
