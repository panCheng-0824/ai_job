"""
内部 API 共用 — 为 ROLE005 构造 LangGraph 绑定。
"""

from __future__ import annotations

from threading import Event

from fastapi import HTTPException

from app.portal import data_catalog
from app.session.role.role005.bindings import build_graph_bindings
from app.session.role.role005.config import resolve_role005_llm_timeout_seconds
from app.session.role.role_util.bindings import GraphBindings
from lc_agent import chat_model_from_entry
from lc_agent.selection import select_model_by_level
from model_cfg import load_model_list
from pipeline_llm import _max_retries

_ROLE005_CODE = "ROLE005"


def create_internal_graph_bindings() -> GraphBindings:
    """
    读取 usermodel 中 ROLE005 条目，创建 LLM + GraphBindings。

    内部 API 使用 temperature=0，保证结构化输出稳定。
    """
    try:
        merged = dict(data_catalog.get_user_model_or_raise(_ROLE005_CODE))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    entry = select_model_by_level(
        load_model_list(), str(merged.get("model_level", "high"))
    )
    llm = chat_model_from_entry(
        entry,
        temperature=0.0,
        timeout=resolve_role005_llm_timeout_seconds(merged),
        max_retries=_max_retries(),
    )
    return build_graph_bindings(merged, llm, Event())
