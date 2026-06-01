"""
ROLE005 — LangGraph 图内状态。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.session.role.role005.domain.models import (
    ContextBundle,
    InterviewPlan,
    InterviewSessionSnapshot,
    PlanIndustryClassification,
    PlanSummary,
)


@dataclass
class PlannerGraphState:
    """
    规划图（``compile_planner_graph``）在节点间传递的状态。

    字段由 ``run_plan_preview_sync`` 初始化，各节点通过返回 dict 增量合并。
    """

    # 简历/岗位等拼好的全文，供 planner_llm 写入 Prompt
    materials_text: str = ""
    # 素材 SHA256 指纹，plan_cache 检索键
    material_hash: str = ""
    # 目标岗位名，Planner 按此岗位出题
    target_role: str = ""
    # 学生档案等补充说明（可选）
    student_context: str = ""
    # 学号：MQ 落库与租户隔离（SSE 来自 merged_user.student_id）
    student_id: str = ""
    session_id: str = ""
    # 命中缓存或 LLM 生成后的大纲；非空则 planner_llm 跳过
    plan: Optional[InterviewPlan] = None
    # 两阶段行业识别结果（Redis 一级桶 → 二级桶 + LLM）
    industry_classification: Optional[PlanIndustryClassification] = None
    # 大纲题库摘要（简介 / 适合人群 / 面试分类）
    plan_summary: Optional[PlanSummary] = None
    # 缓存命中信息、generated 标记等，透传至 PlanPreviewResult
    cache_meta: Dict[str, Any] = field(default_factory=dict)
    # MQ 投递结果（失败不阻断预览，见 mq_error）
    mq_published: bool = False
    mq_error: str = ""
    # 任节点失败时写入，invoke 结束后由入口抛 RuntimeError
    error: str = ""


@dataclass
class InterviewGraphState:
    """答题主循环图状态。"""

    context: Optional[ContextBundle] = None
    turn_action: str = "answer"
    turn_payload: Dict[str, Any] = field(default_factory=dict)
    user_query: str = ""
    # 当前题索引（与 session 同步，图内可临时推进）
    question_index: int = 0
    # Agent 产出
    interviewer_json: Dict[str, Any] = field(default_factory=dict)
    evaluator_json: Dict[str, Any] = field(default_factory=dict)
    scorer_json: Dict[str, Any] = field(default_factory=dict)
    clarifier_text: str = ""
    final_answer: str = ""
    turn_result: Dict[str, Any] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: str = ""


def session_from_bundle(bundle: ContextBundle) -> InterviewSessionSnapshot:
    """从上下文包取出会话快照。"""
    return bundle.session


def plan_from_bundle(bundle: ContextBundle) -> InterviewPlan:
    """从上下文包取出大纲。"""
    return bundle.plan
