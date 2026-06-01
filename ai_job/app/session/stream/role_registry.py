"""
usercode → 角色流式入口注册表。

新增角色时在此登记，避免在 by_model 中 elongate if-elif 链。
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from app.session.chat_stream_context import ChatStreamRunContext
from app.session.role.role_001 import stream_chat_service_tokens as stream_role001
from app.session.role.role_002 import stream_chat_service_tokens as stream_role002
from app.session.role.role_003 import stream_chat_service_tokens as stream_role003
from app.session.role.role_004 import stream_chat_service_tokens as stream_role004
from app.session.role.role_005 import stream_chat_service_tokens as stream_role005
from app.session.role.role_006 import stream_chat_service_tokens as stream_role006
from app.session.role.role_007 import stream_chat_service_tokens as stream_role007

# 流式入口统一签名：ChatStreamRunContext → ChatTokenStreamContext
RoleStreamFn = Callable[[ChatStreamRunContext], Dict[str, Any]]

ROLE_STREAM_REGISTRY: Dict[str, RoleStreamFn] = {
    "ROLE001": stream_role001,
    "ROLE002": stream_role002,
    "ROLE003": stream_role003,
    "ROLE004": stream_role004,
    "ROLE005": stream_role005,
    "ROLE006": stream_role006,
}

DEFAULT_ROLE_STREAM = stream_role007


def resolve_role_stream(usercode: str) -> RoleStreamFn:
    """按 usercode 解析角色流式实现；未知角色回退 ROLE007 测试机器人。"""
    code = (usercode or "").strip()
    return ROLE_STREAM_REGISTRY.get(code, DEFAULT_ROLE_STREAM)


def role_display_name_for(usercode: str) -> str:
    """注册表附带的角色中文名（仅用于日志/注释）。"""
    names = {
        "ROLE001": "岗位规划师",
        "ROLE002": "心理咨询师",
        "ROLE003": "贴心辅导员",
        "ROLE004": "简历优化师",
        "ROLE005": "模拟面试官",
        "ROLE006": "制度咨询师",
    }
    return names.get(usercode, "测试聊天机器人")
