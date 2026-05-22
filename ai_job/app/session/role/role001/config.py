"""ROLE001 配置解析（实现见 ``app.session.role.role_util.config``）。"""

from app.session.role.role_util.config import (
    build_plan_execute_role_block,
    format_common_mistakes,
    resolve_use_structured_return,
    tools_from_user_model,
)

__all__ = [
    "build_plan_execute_role_block",
    "format_common_mistakes",
    "resolve_use_structured_return",
    "tools_from_user_model",
]
