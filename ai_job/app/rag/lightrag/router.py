"""LightRAG 路由：提供写入、查询与图谱 CRUD 接口。"""

from __future__ import annotations

import logging
import traceback
import uuid

from fastapi import APIRouter, HTTPException

from .runtime import LightRAGUnavailableError
from .schemas import (
    GraphEntityCreateRequest,
    GraphEntityUpdateRequest,
    GraphRelationCreateRequest,
    GraphRelationUpdateRequest,
    LightRAGInsertRequest,
    LightRAGQueryRequest,
)
from .service import get_lightrag_service

router = APIRouter()
log = logging.getLogger(__name__)


def _step(trace_id: str, step_no: int, message: str, *args) -> None:
    """输出带顺序标识的步骤日志。"""
    log.info("[trace=%s][step=%02d] " + message, trace_id, step_no, *args)


@router.post("/api/rag/lightrag/insert")
async def lightrag_insert(payload: LightRAGInsertRequest):
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 LightRAG 写入请求")
    if payload.job_ids is not None and len(payload.job_ids) != len(payload.texts):
        raise HTTPException(
            status_code=400,
            detail="job_ids 与 texts 必须等长，且按索引一一对应（含占位空字符串的条目）",
        )
    texts: list[str] = []
    aligned_job_ids: list[str] = []
    for i, raw in enumerate(payload.texts):
        t = str(raw).strip()
        if not t:
            continue
        if payload.job_ids is not None:
            jid = str(payload.job_ids[i]).strip()
            if not jid:
                raise HTTPException(status_code=400, detail=f"第{i + 1}条非空文本对应的 job_id 不能为空")
            aligned_job_ids.append(jid)
        texts.append(t)
    _step(trace_id, 2, "请求参数校验完成, inputCount=%s, validCount=%s", len(payload.texts), len(texts))
    if not texts:
        raise HTTPException(status_code=400, detail="texts 不能为空")
    job_ids_param = aligned_job_ids if payload.job_ids is not None else None
    try:
        _step(trace_id, 3, "开始获取 LightRAG 服务单例")
        service = get_lightrag_service()
        _step(trace_id, 4, "开始调用 insert_texts 执行写入, hasJobIds=%s", job_ids_param is not None)
        count, upload_ids = await service.insert_texts(texts, job_ids=job_ids_param)
        _step(trace_id, 5, "insert_texts 调用成功, inserted=%s, uploadIds=%s", count, upload_ids)
    except LightRAGUnavailableError as exc:
        log.exception("[trace=%s] LightRAG 写入失败, 原因=运行环境不可用", trace_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        detail = f"LightRAG 写入失败: {exc.__class__.__name__}: {exc}"
        stack = traceback.format_exc()
        log.error("[trace=%s] LightRAG 写入异常, detail=%s\n%s", trace_id, detail, stack)
        raise HTTPException(status_code=502, detail=detail) from exc
    return {
        "success": True,
        "inserted": count,
        "upload_ids": upload_ids,
        **service.storage_info(),
    }


@router.post("/api/rag/lightrag/query")
async def lightrag_query(payload: LightRAGQueryRequest):
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 LightRAG 查询请求")
    q = (payload.query or "").strip()
    _step(trace_id, 2, "请求参数校验完成, mode=%s, top_k=%s, questionLength=%s", payload.mode, payload.top_k, len(q))
    if not q:
        raise HTTPException(status_code=400, detail="query 不能为空")
    try:
        _step(trace_id, 3, "开始获取 LightRAG 服务单例")
        service = get_lightrag_service()
        _step(trace_id, 4, "开始调用 query 执行检索")
        answer = await service.query(
            q,
            mode=(payload.mode or "mix").strip() or "mix",
            top_k=max(1, int(payload.top_k)),
            only_need_context=bool(payload.only_need_context),
            only_need_prompt=bool(payload.only_need_prompt),
        )
        _step(trace_id, 5, "query 调用成功, answerLength=%s", len(str(answer or "")))
    except LightRAGUnavailableError as exc:
        log.exception("[trace=%s] LightRAG 查询失败, 原因=运行环境不可用", trace_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        detail = f"LightRAG 查询失败: {exc.__class__.__name__}: {exc}"
        stack = traceback.format_exc()
        log.error("[trace=%s] LightRAG 查询异常, detail=%s\n%s", trace_id, detail, stack)
        raise HTTPException(status_code=502, detail=detail) from exc
    return {
        "query": q,
        "mode": (payload.mode or "mix").strip() or "mix",
        "top_k": max(1, int(payload.top_k)),
        "only_need_context": bool(payload.only_need_context),
        "only_need_prompt": bool(payload.only_need_prompt),
        **service.storage_info(),
        "answer": str(answer or "").strip(),
    }


@router.post("/api/rag/graph/entities")
async def create_graph_entity(payload: GraphEntityCreateRequest):
    """步骤：参数校验 -> 调用服务创建实体 -> 返回创建结果。"""
    entity_name = (payload.entity_name or "").strip()
    log.info("图谱实体创建请求开始, entity_name=%s", entity_name)
    if not entity_name:
        raise HTTPException(status_code=400, detail="entity_name 不能为空")
    try:
        result = await get_lightrag_service().create_entity(entity_name, dict(payload.data or {}))
        log.info("图谱实体创建成功, entity_name=%s", entity_name)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"创建实体失败: {exc}") from exc
    return {"success": True, "entity_name": entity_name, "result": result}


@router.get("/api/rag/graph/entities/{entity_name}")
async def get_graph_entity(entity_name: str):
    """步骤：参数校验 -> 调用服务读取实体 -> 返回查询结果。"""
    name = (entity_name or "").strip()
    log.info("图谱实体查询请求开始, entity_name=%s", name)
    if not name:
        raise HTTPException(status_code=400, detail="entity_name 不能为空")
    try:
        result = await get_lightrag_service().get_entity(name)
        log.info("图谱实体查询成功, entity_name=%s", name)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"查询实体失败: {exc}") from exc
    return {"entity_name": name, "result": result}


@router.put("/api/rag/graph/entities/{entity_name}")
async def update_graph_entity(entity_name: str, payload: GraphEntityUpdateRequest):
    """步骤：参数校验 -> 调用服务更新实体 -> 返回更新结果。"""
    name = (entity_name or "").strip()
    log.info("图谱实体更新请求开始, entity_name=%s", name)
    if not name:
        raise HTTPException(status_code=400, detail="entity_name 不能为空")
    if not payload.data:
        raise HTTPException(status_code=400, detail="data 不能为空")
    try:
        result = await get_lightrag_service().update_entity(name, dict(payload.data))
        log.info("图谱实体更新成功, entity_name=%s", name)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"更新实体失败: {exc}") from exc
    return {"success": True, "entity_name": name, "result": result}


@router.delete("/api/rag/graph/entities/{entity_name}")
async def delete_graph_entity(entity_name: str):
    """步骤：参数校验 -> 调用服务删除实体 -> 返回删除结果。"""
    name = (entity_name or "").strip()
    log.info("图谱实体删除请求开始, entity_name=%s", name)
    if not name:
        raise HTTPException(status_code=400, detail="entity_name 不能为空")
    try:
        result = await get_lightrag_service().delete_entity(name)
        log.info("图谱实体删除成功, entity_name=%s", name)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"删除实体失败: {exc}") from exc
    return {"success": True, "entity_name": name, "result": result}


@router.post("/api/rag/graph/relations")
async def create_graph_relation(payload: GraphRelationCreateRequest):
    """步骤：参数校验 -> 调用服务创建关系 -> 返回创建结果。"""
    src_id = (payload.src_id or "").strip()
    tgt_id = (payload.tgt_id or "").strip()
    log.info("图谱关系创建请求开始, src_id=%s, tgt_id=%s", src_id, tgt_id)
    if not src_id or not tgt_id:
        raise HTTPException(status_code=400, detail="src_id 与 tgt_id 不能为空")
    try:
        result = await get_lightrag_service().create_relation(src_id, tgt_id, dict(payload.data or {}))
        log.info("图谱关系创建成功, src_id=%s, tgt_id=%s", src_id, tgt_id)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"创建关系失败: {exc}") from exc
    return {"success": True, "src_id": src_id, "tgt_id": tgt_id, "result": result}


@router.get("/api/rag/graph/relations")
async def get_graph_relation(src_id: str, tgt_id: str):
    """步骤：参数校验 -> 调用服务查询关系 -> 返回查询结果。"""
    src = (src_id or "").strip()
    tgt = (tgt_id or "").strip()
    log.info("图谱关系查询请求开始, src_id=%s, tgt_id=%s", src, tgt)
    if not src or not tgt:
        raise HTTPException(status_code=400, detail="src_id 与 tgt_id 不能为空")
    try:
        result = await get_lightrag_service().get_relation(src, tgt)
        log.info("图谱关系查询成功, src_id=%s, tgt_id=%s", src, tgt)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"查询关系失败: {exc}") from exc
    return {"src_id": src, "tgt_id": tgt, "result": result}


@router.put("/api/rag/graph/relations")
async def update_graph_relation(src_id: str, tgt_id: str, payload: GraphRelationUpdateRequest):
    """步骤：参数校验 -> 调用服务更新关系 -> 返回更新结果。"""
    src = (src_id or "").strip()
    tgt = (tgt_id or "").strip()
    log.info("图谱关系更新请求开始, src_id=%s, tgt_id=%s", src, tgt)
    if not src or not tgt:
        raise HTTPException(status_code=400, detail="src_id 与 tgt_id 不能为空")
    if not payload.data:
        raise HTTPException(status_code=400, detail="data 不能为空")
    try:
        result = await get_lightrag_service().update_relation(src, tgt, dict(payload.data))
        log.info("图谱关系更新成功, src_id=%s, tgt_id=%s", src, tgt)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"更新关系失败: {exc}") from exc
    return {"success": True, "src_id": src, "tgt_id": tgt, "result": result}


@router.delete("/api/rag/graph/relations")
async def delete_graph_relation(src_id: str, tgt_id: str):
    """步骤：参数校验 -> 调用服务删除关系 -> 返回删除结果。"""
    src = (src_id or "").strip()
    tgt = (tgt_id or "").strip()
    log.info("图谱关系删除请求开始, src_id=%s, tgt_id=%s", src, tgt)
    if not src or not tgt:
        raise HTTPException(status_code=400, detail="src_id 与 tgt_id 不能为空")
    try:
        result = await get_lightrag_service().delete_relation(src, tgt)
        log.info("图谱关系删除成功, src_id=%s, tgt_id=%s", src, tgt)
    except LightRAGUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail=f"当前 LightRAG 版本不支持该操作: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"删除关系失败: {exc}") from exc
    return {"success": True, "src_id": src, "tgt_id": tgt, "result": result}
