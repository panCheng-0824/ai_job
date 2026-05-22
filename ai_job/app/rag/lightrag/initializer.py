"""LightRAG 初始化流程拆分模块。"""

from __future__ import annotations

import logging
import time
from typing import Any

from .config import LightRAGConfig, resolve_lightrag_working_dir
from .runtime import build_openai_funcs, load_light_rag_symbols, select_llm_entry
from .trace import step

log = logging.getLogger(__name__)


async def initialize_rag_instance(config: LightRAGConfig, op_id: str) -> Any:
    """按标准流程初始化 LightRAG 实例并返回对象。"""
    started = time.perf_counter()
    step(log, op_id, 2, "初始化开始, 加载运行时符号")
    LightRAG, _, _ = load_light_rag_symbols()

    step(log, op_id, 3, "初始化继续, 按 type+level 选择聊天模型")
    entry = select_llm_entry(config.model_level)

    step(log, op_id, 4, "初始化继续, 构建 llm 与 embedding 函数")
    llm_func, embedding_func = build_openai_funcs(entry)

    working_dir = resolve_lightrag_working_dir(config)
    step(log, op_id, 5, "初始化继续, 准备工作目录, working_dir=%s", str(working_dir))
    working_dir.mkdir(parents=True, exist_ok=True)

    log.info(
        "LightRAG 初始化参数确认, workspace=%s, graph_storage=%s, vector_storage=%s, working_dir=%s",
        config.workspace,
        config.graph_storage,
        config.vector_storage,
        str(working_dir),
    )
    rag = LightRAG(
        working_dir=str(working_dir),
        workspace=config.workspace,
        llm_model_func=llm_func,
        embedding_func=embedding_func,
        graph_storage=config.graph_storage,
        vector_storage=config.vector_storage,
    )
    step(log, op_id, 6, "初始化继续, 执行存储层初始化")
    await rag.initialize_storages()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    step(log, op_id, 7, "初始化完成, elapsedMs=%s", elapsed_ms)
    return rag
