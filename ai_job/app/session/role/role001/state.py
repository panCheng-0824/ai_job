"""
ROLE001 LangGraph 状态定义。

图内各节点通过读写 ``JobPlanExecuteState`` 传递「规划步骤、执行观测、最终答复」。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.session.role.role001.intent import Role001Intent


@dataclass
class JobPlanExecuteState:
    """
    Plan-and-Execute 在图内传递的状态容器。

    字段说明
    --------
    question:
        本轮完整语境载体，由流式入口拼装：系统提示 + 历史摘要 + 用户当前句。
        各节点不再单独维护 system/user 消息列表，统一读本字段。
    plan:
        planner 节点输出的子步骤列表（JSON 字符串数组解析结果）。
    step_index:
        下一个待 executor 处理的步骤下标；等于 ``len(plan)`` 时表示步骤已全部执行完。
    observations:
        与 ``plan`` 顺序对齐的每步观测文本（模型短文 + 工具返回拼接）。
    structured_payload:
        ``structured_return`` 节点产出的 JSON 字符串（美化后），供日志或二次消费。
    final_answer:
        面向用户的完整答复（Markdown；结构化模式下含 summary + JSON 代码块）。
    user_query:
        用户本轮原句；推荐快车道作为 LightRAG 检索 query，与 ``question`` 完整载体区分。
    student_context:
        学生档案摘要（来自 ``system_prompt_extra`` / ``format_student_profile_prompt_extra``）。
    intent:
        入口路由器结果：``job_recommend``（快车道）或 ``career_consult``（慢车道 Plan-and-Execute）。
    job_recommend:
        快车道岗位推荐结构化结果（与 ``/api/skills/job-info-query`` 同构），供前端交互组件渲染。
    """

    question: str = ""
    user_query: str = ""
    student_context: str = ""
    intent: Role001Intent = "career_consult"
    plan: List[str] = field(default_factory=list)
    step_index: int = 0
    observations: List[str] = field(default_factory=list)
    structured_payload: str = ""
    final_answer: str = ""
    job_recommend: Dict[str, Any] = field(default_factory=dict)
