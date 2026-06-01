"""
ROLE005 — 面试大纲语义缓存（Milvus 检索占位 + 降级）。

P1 接入 Milvus；P0 未命中时直接走新规划。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from app.session.role.role005.domain.models import InterviewPlan

log = logging.getLogger(__name__)


def search_plan_cache(
    material_hash: str,
    target_role: str,
) -> Tuple[Optional[InterviewPlan], Dict[str, Any]]:
    """
    按素材指纹检索相似大纲缓存。

    返回 (plan, cache_meta)；未命中时 plan 为 None。
    """
    _ = target_role
    # TODO: 接入 Milvus collection `interview_plan`，参考 job_info semantic_cache
    log.debug("面试大纲缓存未启用或未命中 hash=%s", material_hash)
    return None, {
        "hit": False,
        "similarity": 0.0,
        "message": "未命中语义缓存，将生成新大纲",
    }
