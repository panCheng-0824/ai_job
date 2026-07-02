"""
ROLE005 — 面试大纲规划 Agent（高级模型）。

产出 ``InterviewPlan`` 供 server_job 落库，并驱动后续「面试记录表」与按题新开深挖会话。
每道 ``questions[]`` 条目是**单题深挖的入口**，须在 ``eval_criteria`` 中写清考查方向与挖掘轴线。
"""

from __future__ import annotations

import uuid

from app.session.role.role005.agents._llm import invoke_llm_json_object
from app.session.role.role005.domain.models import InterviewPlan, QuestionItem
from app.session.role.role005.infra.schema_gate import validate_interview_plan
from app.session.role.role005.parsing import parse_json_object
from app.session.role.role_util.bindings import GraphBindings

# eval_criteria 推荐键（与 server_job 记录表 / 子会话 Agent 约定，均为中文短句或字符串数组）
_EVAL_CRITERIA_EXAM_FOCUS = "exam_focus"
_EVAL_CRITERIA_DEEP_DIVE_AXES = "deep_dive_axes"
_EVAL_CRITERIA_RESUME_ANCHOR = "resume_anchor"
_EVAL_CRITERIA_JOB_ANCHOR = "job_anchor"
_EVAL_CRITERIA_RECORD_ENTRY = "record_sheet_entry"


def build_planner_prompt(
    *,
    role_block: str,
    materials_block: str,
    target_role: str,
    student_context: str,
) -> str:
    """
    构造 Planner Prompt：生成可落库、可驱动记录表与按题深挖会话的结构化大纲。

    设计原则
    --------
    - ``text`` 是面向学生的**入口题面**（简洁、可独立成题），不是宽泛话题；
    - ``dimensions`` 标明能力/知识考查维度标签；
    - ``eval_criteria`` 必须写清考查方向与深层次挖掘方向，供记录表与子 Agent 复用；
    - ``preset_followups`` 与 ``deep_dive_axes`` 对齐，作为后续 ReAct 深挖的候选追问。
    """
    return f"""你是面试大纲规划专家。你的任务是为目标岗位「{target_role}」编排**可执行、可溯源**的结构化面试大纲。

## 业务背景（必须理解）

1. 本大纲会持久化，并据此为学生生成**面试记录表**（逐题进度、评分、标注）。
2. 记录表中**每一道大纲题都是独立入口**：后续会针对单题**新开一场会话**，子 Agent 仅围绕该题的考查方向与挖掘轴线进行 ReAct 式深挖（结合简历与岗位问业务/场景题，直到本题结束再写回记录表）。
3. 因此：**题面指向不准，整条深挖链路都会偏**。禁止出「谈谈你的优缺点」「介绍一下自己」等泛化题充数；每题必须能对应简历或岗位 JD 中的具体经历/技能/业务点。

## 输出格式

1. 输出**仅一个** JSON 对象，不要 Markdown 围栏，不要任何解释性正文。
2. 顶层字段：version=1、target_role、questions 数组。
3. 题目数量 **8～10 道**；其中 **至少 40%** 为结合简历项目/岗位 JD 的业务或场景题（在 eval_criteria 的 resume_anchor / job_anchor 中写明依据）。

## 每题 questions 元素（全部必填语义，字段不可缺省）

| 字段 | 要求 |
|------|------|
| id | 稳定题号，如 q1、q2 |
| text | **入口题面**：一句话或短段，学生能直接作答；避免过大、过空 |
| dimensions | 2～4 个字符串，能力/知识**考查维度**标签（如「分布式一致性」「业务抽象」「沟通表达」） |
| weight | 0.5～2.0，重要题可更高 |
| thinking_hint | 给学生的作答提示（**不得**含标准答案或关键结论） |
| timeout_seconds | 建议 240～600 |
| preset_followups | 2～4 条字符串，**预设深挖追问**（与子 Agent 追问方向一致，供记录表/深挖会话参考） |
| reference_answer | **内部**参考答案要点（面试官环节不展示） |
| eval_criteria | 对象，**必须**包含下列键（值均为中文，除数组外）： |

### eval_criteria 必填键说明

- ``{_EVAL_CRITERIA_EXAM_FOCUS}``（string）：本题**考查方向**——一句话说明「要验证什么能力/知识」，须可检验。
- ``{_EVAL_CRITERIA_DEEP_DIVE_AXES}``（string[]）：**深层次挖掘方向**——3～5 条追问轴线（如「决策依据」「失败与回滚」「指标与边界」「与岗位业务的结合点」）；后续单题会话将沿这些轴线 ReAct 挖掘。
- ``{_EVAL_CRITERIA_RESUME_ANCHOR}``（string）：本题绑定的**简历锚点**（项目/经历/技能，无则写「通用题，不绑简历」）。
- ``{_EVAL_CRITERIA_JOB_ANCHOR}``（string）：本题绑定的**岗位/JD 锚点**（职责/技能/业务场景，无则写「通用题，不绑岗位」）。
- ``{_EVAL_CRITERIA_RECORD_ENTRY}``（string）：**记录表入口说明**——说明该题在记录表中作为第几类关卡、新开深挖会话时子 Agent 应优先遵循的主线（1～2 句）。

可选扩展键（建议写）：``scoring_notes``（评分关注点）、``intent_handlers``（学生答「不会/要提示/澄清」时的处理倾向，仅方向不写答案）。

## 编排策略

- 题序：由浅入深（基础 → 项目/场景 → 综合/压力），避免重复考查同一简历片段。
- 同一 ``deep_dive_axes`` 轴线在不同题之间尽量不重复。
- ``preset_followups`` 必须是可执行的问句，不要写「继续追问」等空话。

──角色约束──
{role_block}

──学生档案摘要──
{student_context or "（无）"}

──简历与岗位素材──
{materials_block}

JSON 示例（仅结构参考，内容须替换为真实素材）：
{{"plan_id":"plan_xxx","version":1,"target_role":"{target_role}","questions":[{{"id":"q1","text":"结合你在XX项目中的缓存改造，说明一致性方案选型过程","dimensions":["分布式系统","技术决策","业务理解"],"weight":1.2,"thinking_hint":"可按背景、方案对比、落地结果组织","timeout_seconds":360,"preset_followups":["若出现热点 key 抖动你会如何演进？","如何向业务方解释短暂不一致？"],"reference_answer":"内部要点…","eval_criteria":{{"{_EVAL_CRITERIA_EXAM_FOCUS}":"验证其在真实项目中的分布式选型与权衡能力","{_EVAL_CRITERIA_DEEP_DIVE_AXES}":["选型对比维度","一致性与可用性权衡","监控与回滚","业务沟通"],"{_EVAL_CRITERIA_RESUME_ANCHOR}":"简历项目 XX 缓存改造","{_EVAL_CRITERIA_JOB_ANCHOR}":"岗位 JD 中高性能/中间件要求","{_EVAL_CRITERIA_RECORD_ENTRY}":"记录表第2题入口；新会话仅沿缓存一致性主线深挖直至评分结案"}}}}]}}
"""


def run_planner_agent(
    bindings: GraphBindings,
    *,
    materials_block: str,
    target_role: str,
    student_context: str,
    material_hash: str,
    planner_model: str = "",
) -> tuple[InterviewPlan | None, str]:
    """
    调用 LLM 生成 InterviewPlan。

    返回 (plan, error_message)。
    """
    prompt = build_planner_prompt(
        role_block=bindings.role_block,
        materials_block=materials_block,
        target_role=target_role,
        student_context=student_context,
    )
    # response_format=json_object，降低 Markdown 围栏导致的 JSON 解析失败
    raw = invoke_llm_json_object(bindings, prompt, scenario="模拟面试-规划生成")
    data, parse_err = parse_json_object(raw)
    if parse_err:
        return None, parse_err

    # 补全 plan_id / hash / model 溯源
    if not data.get("plan_id"):
        data["plan_id"] = f"plan_{uuid.uuid4().hex[:12]}"
    data["version"] = int(data.get("version") or 1)
    data["target_role"] = data.get("target_role") or target_role
    data["source_material_hash"] = material_hash
    data["planner_model"] = planner_model or str(
        bindings.identity.get("model_level") or ""
    )

    plan, err = validate_interview_plan(data)
    if err or plan is None:
        # 降级：尝试仅解析 questions 列表
        if isinstance(data.get("questions"), list):
            try:
                items = [QuestionItem.model_validate(q) for q in data["questions"]]
                plan = InterviewPlan(
                    plan_id=str(data.get("plan_id")),
                    version=1,
                    target_role=target_role,
                    source_material_hash=material_hash,
                    questions=items,
                )
                return plan, ""
            except Exception as exc2:
                return None, f"题目列表校验失败: {exc2}"
        return None, err or "大纲无效"
    return plan, ""
