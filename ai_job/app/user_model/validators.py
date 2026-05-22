"""用户模型与角色配置 JSON 的校验辅助函数。"""

from __future__ import annotations

from typing import Any, MutableMapping, cast

from .types import PipelineRoleProfile, UserModel

REQUIRED_USER_KEYS = (
    "username",
    "usercode",
    "user_profile",
    "goals",
    "sys_prompt",
    "user_prompt",
    "model_level",
)


def validate_one_pipeline_role(key: str, raw: MutableMapping[str, Any]) -> PipelineRoleProfile:
    """校验单个管道角色配置对象。"""
    need = ("username", "usercode", "sys_prompt", "model_level")
    missing = [k for k in need if k not in raw]
    if missing:
        raise KeyError(f"role_profiles[{key!r}] missing keys: {missing}")
    if not isinstance(raw["username"], str) or not str(raw["username"]).strip():
        raise ValueError(f"role_profiles[{key!r}].username must be non-empty")
    if not isinstance(raw["usercode"], str) or not str(raw["usercode"]).strip():
        raise ValueError(f"role_profiles[{key!r}].usercode must be non-empty")
    if not isinstance(raw["sys_prompt"], str) or not str(raw["sys_prompt"]).strip():
        raise ValueError(f"role_profiles[{key!r}].sys_prompt must be non-empty")
    if not isinstance(raw["model_level"], str) or not str(raw["model_level"]).strip():
        raise ValueError(f"role_profiles[{key!r}].model_level must be non-empty")
    if "output_schema_path" in raw and raw["output_schema_path"] is not None:
        if not isinstance(raw["output_schema_path"], str) or not str(raw["output_schema_path"]).strip():
            raise ValueError(f"role_profiles[{key!r}].output_schema_path must be a non-empty string when set")
    if "structured_primary_field" in raw and raw["structured_primary_field"] is not None:
        if not isinstance(raw["structured_primary_field"], str):
            raise ValueError(f"role_profiles[{key!r}].structured_primary_field must be a string when set")
    return cast(PipelineRoleProfile, raw)


def validate_one_user(raw: MutableMapping[str, Any]) -> UserModel:
    """校验 `usermodel.json` 中的单个用户对象。"""
    missing = [k for k in REQUIRED_USER_KEYS if k not in raw]
    if missing:
        raise KeyError(f"usermodel item missing keys: {missing}")

    if not isinstance(raw["username"], str) or not raw["username"].strip():
        raise ValueError("username must be a non-empty string")
    if not isinstance(raw["usercode"], str) or not raw["usercode"].strip():
        raise ValueError("usercode must be a non-empty string")

    profile = raw["user_profile"]
    if not isinstance(profile, dict):
        raise ValueError("user_profile must be an object")

    goals = raw["goals"]
    if not isinstance(goals, list) or not all(isinstance(g, str) for g in goals):
        raise ValueError("goals must be an array of strings")

    memory = raw.get("context_memory", [])
    if not isinstance(memory, list):
        raise ValueError("context_memory must be an array")
    for turn in memory:
        if not isinstance(turn, dict):
            raise ValueError("each context_memory item must be an object")
        if turn.get("role") not in ("user", "assistant"):
            raise ValueError('context_memory role must be "user" or "assistant"')
        if "content" not in turn or not isinstance(turn["content"], str):
            raise ValueError("context_memory items need string content")

    tools = raw.get("tools", [])
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        raise ValueError("tools must be an array of strings")

    for key in ("sys_prompt", "user_prompt", "model_level"):
        if not isinstance(raw[key], str):
            raise ValueError(f"{key} must be a string")

    optional_str_keys = (
        "greeting_example",
        "conversation_exit",
        "clarification_question",
        "output_format",
        "risk_reminder",
    )
    for key in optional_str_keys:
        if key in raw and raw[key] is not None and not isinstance(raw[key], str):
            raise ValueError(f"{key} must be a string when set")

    if "common_mistakes" in raw and raw["common_mistakes"] is not None:
        mistakes = raw["common_mistakes"]
        if isinstance(mistakes, str):
            pass
        elif isinstance(mistakes, list) and all(isinstance(item, str) for item in mistakes):
            pass
        else:
            raise ValueError("common_mistakes must be a string or an array of strings")

    if "forbidden_topics" in raw and raw["forbidden_topics"] is not None:
        topics = raw["forbidden_topics"]
        if not isinstance(topics, list) or not all(isinstance(item, str) for item in topics):
            raise ValueError("forbidden_topics must be an array of strings when set")

    current_question = raw.get("current_question", "")
    if not isinstance(current_question, str):
        raise ValueError("current_question must be a string")

    raw["context_memory"] = memory
    raw["tools"] = tools
    raw["current_question"] = current_question

    return cast(UserModel, raw)
