"""
ROLE005 — 规划预览完成后展示给学生的摘要文案格式化。

与 ``iter_plan_preview_tokens`` 解耦，便于单独调整 Markdown 结构而不改动 SSE 主流程。
"""

from __future__ import annotations

from app.session.role.role005.domain.models import PlanPreviewResult


def format_plan_preview_answer(preview: PlanPreviewResult) -> str:
    """
    将规划结果格式化为聊天气泡 Markdown 正文。

    须包含「确认后可创建正式面试会话」短语，供 web_job 识别并展示「开始」按钮。
    """
    plan = preview.plan
    ps = preview.plan_summary
    lines: list[str] = []

    if ps and (ps.introduction or "").strip():
        lines.append(ps.introduction.strip())
        lines.append("")

    lines.append("### 面试大纲已就绪")
    lines.append("")
    lines.append(f"- **题目编号**：`{plan.plan_id}`")
    lines.append(f"- **题量**：{len(plan.questions)} 道")
    if (plan.target_role or "").strip():
        lines.append(f"- **目标岗位**：{plan.target_role.strip()}")

    if ps and (ps.suitable_audience or "").strip():
        lines.append(f"- **适合人群**：{ps.suitable_audience.strip()}")

    if ps and ps.interview_categories:
        cats = "、".join(c for c in ps.interview_categories if c)
        if cats:
            lines.append(f"- **考查模块**：{cats}")

    ic = preview.industry_classification
    if ic and (ic.industry_category_name or "").strip():
        top = (ic.top_category_name or "").strip()
        sub = ic.industry_category_name.strip()
        industry_line = f"{top} / {sub}" if top else sub
        lines.append(f"- **行业分类**：{industry_line}")

    lines.append("")
    lines.append(
        "大纲已同步至题库。**确认后可创建正式面试会话**，请点击下方「开始」进入模拟面试。"
    )
    return "\n".join(lines)
