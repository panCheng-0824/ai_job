"""
ROLE005 模拟面试官 — AI 计算层（无业务库写入）。

目录说明
--------
- ``domain/``：Pydantic 契约与图状态
- ``graph/``：规划图、答题图及节点
- ``agents/``：Planner / Interviewer / Evaluator / Scorer / Clarifier
- ``materials/``：简历与岗位卡片素材提取
- ``stream_handlers/``：SSE 分模式处理（由 ``stream.py`` 导出）
- ``api/``：server_job 调用的内部 HTTP
- ``infra/``：Schema 门禁、context-bundle 回调
- ``mq/``：RocketMQ 异步任务（ai_job_b）

业务进度、幂等、审计由 server_job + MySQL 负责。
"""

from app.session.role.role005.stream import (
    ChatTokenStreamContext,
    stream_chat_service_tokens,
)
from app.session.role.role005.graph.planner_graph import run_plan_preview_sync
from app.session.role.role005.graph.interview_graph import run_interview_turn_sync

__all__ = [
    "ChatTokenStreamContext",
    "stream_chat_service_tokens",
    "run_plan_preview_sync",
    "run_interview_turn_sync",
]
