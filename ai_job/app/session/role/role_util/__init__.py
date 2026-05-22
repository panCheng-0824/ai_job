"""
角色流水线共用工具（从 ROLE001 抽取，供各角色包复用）。

- ``parsing``：Markdown JSON 围栏剥离、规划步骤与结构化块解析
- ``config``：用户模型 → 角色约束块、工具列表、结构化收尾开关
- ``stream_common``：流式入口常用的用户模型合并、历史摘录、问题载体拼装
- ``bindings``：LangGraph 运行时依赖 ``GraphBindings`` 与中止检测
- ``intent_mode``：``stream_options`` 中的意图模式覆盖读取
"""

from app.session.role.role_util.bindings import GraphBindings, is_cancelled
from app.session.role.role_util.config import (
    build_plan_execute_role_block,
    build_role_block,
    format_common_mistakes,
    resolve_use_structured_return,
    tools_from_user_model,
)
from app.session.role.role_util.intent_mode import resolve_stream_option_mode
from app.session.role.role_util.parsing import (
    parse_plan_json,
    parse_structured_blob,
    strip_markdown_json_fence,
)
from app.session.role.role_util.stream_common import (
    ChatTokenStreamContext,
    build_full_question,
    chunk_text,
    merge_stream_user,
    prepare_question_and_history,
    role_display_name,
)

__all__ = [
    "ChatTokenStreamContext",
    "GraphBindings",
    "build_full_question",
    "build_plan_execute_role_block",
    "build_role_block",
    "chunk_text",
    "format_common_mistakes",
    "is_cancelled",
    "merge_stream_user",
    "parse_plan_json",
    "parse_structured_blob",
    "prepare_question_and_history",
    "resolve_stream_option_mode",
    "resolve_use_structured_return",
    "role_display_name",
    "strip_markdown_json_fence",
    "tools_from_user_model",
]
