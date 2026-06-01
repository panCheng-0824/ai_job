"""
ROLE005 — LangChain 工具定义（与 usermodel tools 名称对齐）。

图节点当前直接调用 agents；工具供后续 ReAct 扩展或外部编排使用。
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.tools import tool


@tool
def load_interview_plan(session_id: str) -> str:
    """加载面试大纲与进度（由 server_job 提供，工具层占位）。"""
    return f"{{\"session_id\": \"{session_id}\", \"note\": \"请通过 server_job context-bundle 加载\"}}"


@tool
def record_answer(session_id: str, question_id: str, answer: str) -> str:
    """记录学生回答（实际写入在 server_job /turn 事务）。"""
    _ = (session_id, question_id, answer)
    return "{\"ok\": true}"


@tool
def evaluate_answer(session_id: str, question_id: str, answer: str) -> str:
    """评估回答是否完整（Evaluator Agent 占位）。"""
    return (
        f"{{\"session_id\": \"{session_id}\", \"question_id\": \"{question_id}\", "
        f"\"status\": \"incomplete\"}}"
    )


@tool
def generate_followup(session_id: str, question_id: str) -> str:
    """生成追问（Interviewer 占位）。"""
    return f"{{\"session_id\": \"{session_id}\", \"followup\": \"请补充更多细节\"}}"


@tool
def check_timeout(session_id: str, question_id: str) -> str:
    """检查是否超时（权威计时在 server_job Redis）。"""
    return (
        f"{{\"session_id\": \"{session_id}\", \"question_id\": \"{question_id}\", "
        f"\"timed_out\": false, \"note\": \"服务端计时为准\"}}"
    )


@tool
def end_interview(session_id: str) -> str:
    """结束面试并触发报告（server_job 负责状态迁移）。"""
    return f"{{\"session_id\": \"{session_id}\", \"status\": \"completed_pending_report\"}}"


INTERVIEW_TOOLS = [
    load_interview_plan,
    record_answer,
    evaluate_answer,
    generate_followup,
    check_timeout,
    end_interview,
]
