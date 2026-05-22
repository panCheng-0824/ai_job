"""用户模型子包：类型定义、校验、加载与提示词构造。"""

from .loader import load_role_profiles, load_user_model, load_user_models
from .prompt_builder import build_system_prompt_from_user
from .types import (
    MemoryTurn,
    PipelineRoleKey,
    PipelineRoleProfile,
    RoleProfilesBundle,
    UserModel,
)

__all__ = [
    "PipelineRoleKey",
    "PipelineRoleProfile",
    "RoleProfilesBundle",
    "MemoryTurn",
    "UserModel",
    "load_role_profiles",
    "load_user_models",
    "load_user_model",
    "build_system_prompt_from_user",
]
