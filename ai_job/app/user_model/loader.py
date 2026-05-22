"""用户模型与角色配置的 JSON 加载器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, MutableMapping, Optional, cast

from .types import PIPELINE_ROLE_KEYS, PipelineRoleProfile, RoleProfilesBundle, UserModel
from .validators import validate_one_pipeline_role, validate_one_user

ROOT = Path(__file__).resolve().parents[2]


def default_user_model_path() -> Path:
    """返回 `usermodel.json` 的默认路径。"""
    return ROOT / "data" / "usermodel.json"


def default_role_profiles_path() -> Path:
    """返回 `role_profiles.json` 的默认路径。"""
    return ROOT / "config" / "role_profiles.json"


def load_role_profiles(cfg_path: Optional[Path] = None) -> RoleProfilesBundle:
    """加载并校验 `role_profiles.json`。"""
    path = cfg_path or default_role_profiles_path()
    with path.open(encoding="utf-8") as f:
        raw: Any = json.load(f)

    if not isinstance(raw, MutableMapping):
        raise ValueError("role_profiles root must be a JSON object")

    bundle: Dict[str, PipelineRoleProfile] = {}
    for key in PIPELINE_ROLE_KEYS:
        if key not in raw:
            raise KeyError(f"role_profiles missing key: {key!r}")
        item = raw[key]
        if not isinstance(item, MutableMapping):
            raise ValueError(f"role_profiles[{key!r}] must be an object")
        bundle[key] = validate_one_pipeline_role(key, item)

    return cast(RoleProfilesBundle, bundle)


def load_user_models(cfg_path: Optional[Path] = None) -> List[UserModel]:
    """加载并校验 `usermodel.json` 的完整用户数组。"""
    path = cfg_path or default_user_model_path()
    with path.open(encoding="utf-8") as f:
        raw: Any = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("usermodel root must be a JSON array")

    users: List[UserModel] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()
    for idx, item in enumerate(raw):
        if not isinstance(item, MutableMapping):
            raise ValueError(f"usermodel[{idx}] must be a JSON object")
        user = validate_one_user(item)
        if user["usercode"] in seen_codes:
            raise ValueError(f"duplicate usercode: {user['usercode']!r}")
        if user["username"] in seen_names:
            raise ValueError(f"duplicate username: {user['username']!r}")
        seen_codes.add(user["usercode"])
        seen_names.add(user["username"])
        users.append(user)

    return users


def load_user_model(
    cfg_path: Optional[Path] = None,
    *,
    username: Optional[str] = None,
    usercode: Optional[str] = None,
) -> UserModel:
    """按 username/usercode 选取用户；都未提供时回退首条记录。"""
    users = load_user_models(cfg_path)
    if not users:
        raise ValueError("usermodel array is empty")

    if username is not None:
        for user in users:
            if user["username"] == username:
                return user
        raise KeyError(f"no user with username={username!r}")

    if usercode is not None:
        for user in users:
            if user["usercode"] == usercode:
                return user
        raise KeyError(f"no user with usercode={usercode!r}")

    return users[0]
