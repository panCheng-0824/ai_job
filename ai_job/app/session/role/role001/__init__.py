"""
ROLE001 — 岗位规划师（Plan-and-Execute + 可选结构化汇总）。

包结构
------
- ``state``：LangGraph 图内状态 ``JobPlanExecuteState``
- ``bindings``：运行时依赖绑定 ``GraphBindings``
- ``parsing``：模型输出 JSON / 围栏解析
- ``config``：从 ``usermodel.json`` 抽取工具列表与角色约束块
- ``nodes``：planner / executor / structured_return / plain_finalize
- ``intent``：入口意图分类（推荐快车道 / 咨询慢车道）
- ``graph``：图编译（含 intent_router）与同步执行入口
- ``stream_handlers`` / ``stream``：SSE 流式对外入口 ``stream_chat_service_tokens``
- ``bindings_factory``：``build_graph_bindings``

兼容：``app.session.role.role_001`` 仍可直接 ``import stream_chat_service_tokens``。
"""

from app.session.role.role001.graph import compile_plan_execute_graph, run_job_plan_execute_sync
from app.session.role.role001.intent import classify_role001_intent
from app.session.role.role001.state import JobPlanExecuteState
from app.session.role.role001.stream import (
    ChatTokenStreamContext,
    stream_chat_service_tokens,
)

__all__ = [
    "ChatTokenStreamContext",
    "JobPlanExecuteState",
    "classify_role001_intent",
    "compile_plan_execute_graph",
    "run_job_plan_execute_sync",
    "stream_chat_service_tokens",
]
