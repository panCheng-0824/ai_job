"""
ROLE005 领域契约 — Pydantic 模型。

与 server_job ``resources/schema/interview/`` 及 MQ ``interview.plan.result`` 载荷字段对齐。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuestionItem(BaseModel):
    """单道面试题（含内部参考答案与 eval_criteria）。"""

    id: str
    text: str
    dimensions: List[str] = Field(default_factory=list)
    weight: float = 1.0
    thinking_hint: str = ""
    timeout_seconds: int = 300
    preset_followups: List[str] = Field(default_factory=list)
    reference_answer: str = ""
    eval_criteria: Dict[str, Any] = Field(default_factory=dict)


class InterviewPlan(BaseModel):
    """面试大纲（版本化，确认后由 server_job 落库）。"""

    plan_id: str
    version: int = 1
    target_role: str = ""
    source_material_hash: str = ""
    rubric_version: str = "v1"
    planner_model: str = ""
    # 两阶段行业识别后的二级 category_id，confirm 时写入 interview_plan_basics
    industry_category_id: str = ""
    questions: List[QuestionItem] = Field(default_factory=list)


class PlanIndustryClassification(BaseModel):
    """大纲行业两阶段识别结果（一级 → 二级）。"""

    top_category_id: str = ""
    top_category_name: str = ""
    industry_category_id: str = Field(default="", description="最终二级 category_id")
    industry_category_name: str = ""
    confidence: float = 0.0
    reason: str = ""
    source: str = "redis_two_stage_llm"


class PlanSummary(BaseModel):
    """
    题目大纲题库摘要（供列表检索与推荐，不含逐题参考答案）。

    由规划图末尾 ``plan_summary`` 节点生成，经 MQ 写入 server_job ``interview_plan_basics`` 等 V2 表。
    """

    introduction: str = Field(default="", description="大纲简介，2～4 句")
    suitable_audience: str = Field(default="", description="适合人群描述")
    interview_categories: List[str] = Field(
        default_factory=list,
        description="面试分类标签，如技术基础、项目深挖、综合表达",
    )


class PlanPreviewResult(BaseModel):
    """规划图同步执行结果（SSE / 内部 API）。"""

    plan: InterviewPlan
    plan_summary: Optional[PlanSummary] = None
    industry_classification: Optional[PlanIndustryClassification] = None
    cache_meta: Dict[str, Any] = Field(default_factory=dict)
    material_hash: str = ""
    mq_published: bool = False
    mq_error: str = ""


class InterviewSessionSnapshot(BaseModel):
    """会话快照（context-bundle 内嵌，非完整 DB 行）。"""

    interview_session_id: str
    student_id: str = ""
    plan_id: str = ""
    plan_version: int = 1
    status: str = "planning"
    phase: str = "self_intro"
    current_question_index: int = 0
    snapshots: Dict[str, Any] = Field(default_factory=dict)


class ContextBundle(BaseModel):
    """单轮答题上下文：会话 + 大纲 + 学生档案。"""

    session: InterviewSessionSnapshot
    plan: InterviewPlan
    student_profile: Dict[str, Any] = Field(default_factory=dict)


class TurnResult(BaseModel):
    """单轮 turn 结构化结果，供 server_job 事务写入。"""

    interview_session_id: str
    action: str = "answer"
    phase: str = ""
    current_question_index: int = 0
    interviewer_output: Dict[str, Any] = Field(default_factory=dict)
    evaluator_output: Dict[str, Any] = Field(default_factory=dict)
    scorer_output: Dict[str, Any] = Field(default_factory=dict)
    session_delta: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: str = ""
    final_answer_text: str = ""


class InterviewReport(BaseModel):
    """面试报告（异步生成后入库）。"""

    report_id: str
    interview_session_id: str
    per_question_scores: List[Dict[str, Any]] = Field(default_factory=list)
    total_score: float = 0.0
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    evidence_quotes: List[str] = Field(default_factory=list)
    interviewer_advice: str = ""
    rubric_version: str = "v1"
    scorer_model: str = ""
    generated_at: str = ""
