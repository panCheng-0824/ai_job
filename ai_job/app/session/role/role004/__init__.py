"""
ROLE004 — 简历优化师（优化建议 + 素材生成结构化简历）。

包结构
------
- ``state``：``ResumeOptimizeState``
- ``materials``：素材篮 / 附加上下文格式化
- ``intent``：``resume_advise`` vs ``resume_generate`` 意图路由
- ``resume_templates``：6 种模版数据格式与中文说明（与 web_job 对齐）
- ``parsing``：按模版 id 解析/规整简历 JSON
- ``nodes`` / ``graph``：LangGraph 双通道
- ``stream``：SSE 入口 ``stream_chat_service_tokens``

兼容：``app.session.role.role_004`` 仍可直接 import。
"""

from app.session.role.role004.graph import compile_resume_optimize_graph, run_resume_optimize_sync
from app.session.role.role004.resume_templates import (
    RESUME_TEMPLATES,
    DEFAULT_TEMPLATE_ID,
    get_template,
    list_template_ids,
    resolve_template_id,
)
from app.session.role.role004.intent import classify_role004_intent
from app.session.role.role004.state import ResumeOptimizeState
from app.session.role.role_util.stream_common import ChatTokenStreamContext
from app.session.role.role004.stream import stream_chat_service_tokens

__all__ = [
    "ChatTokenStreamContext",
    "DEFAULT_TEMPLATE_ID",
    "RESUME_TEMPLATES",
    "ResumeOptimizeState",
    "classify_role004_intent",
    "compile_resume_optimize_graph",
    "get_template",
    "list_template_ids",
    "resolve_template_id",
    "run_resume_optimize_sync",
    "stream_chat_service_tokens",
]
