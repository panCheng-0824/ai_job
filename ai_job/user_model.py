"""用户模型兼容层导出模块。

新代码建议直接从 ``app.user_model`` 子模块导入：
- ``app.user_model.types``
- ``app.user_model.validators``
- ``app.user_model.loader``
- ``app.user_model.prompt_builder``

本文件继续重导出同名公共 API，以避免旧导入路径失效。
"""

from app.user_model import (  # noqa: F401
    MemoryTurn,
    PipelineRoleKey,
    PipelineRoleProfile,
    RoleProfilesBundle,
    UserModel,
    build_system_prompt_from_user,
    load_role_profiles,
    load_user_model,
    load_user_models,
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
