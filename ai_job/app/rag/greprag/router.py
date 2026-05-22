"""GrepRAG 路由：提供写入、检索、文档管理等接口。"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException

from .schemas import (
    GrepRAGInsertRequest,
    GrepRAGQueryRequest,
    GrepRAGReindexRequest,
    GrepRAGTextToMdRequest,
)
from .service import get_greprag_service

router = APIRouter()
log = logging.getLogger(__name__)


def _step(trace_id: str, step_no: int, message: str, *args) -> None:
    """输出带顺序标识的步骤日志。"""
    log.info("[trace=%s][step=%02d] " + message, trace_id, step_no, *args)


@router.post("/api/rag/greprag/insert")
def greprag_insert(payload: GrepRAGInsertRequest):
    """步骤：校验文本 -> 调用服务写入 -> 返回写入条数。"""
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 GrepRAG 写入请求")
    texts = [str(x).strip() for x in payload.texts if str(x).strip()]
    _step(trace_id, 2, "请求参数校验完成, input_count=%s, valid_count=%s", len(payload.texts), len(texts))
    if not texts:
        raise HTTPException(status_code=400, detail="texts 不能为空")
    _step(trace_id, 3, "开始调用 insert_texts 执行写入")
    count = get_greprag_service().insert_texts(texts, source=(payload.source or "manual").strip() or "manual")
    _step(trace_id, 4, "写入成功, inserted=%s", count)
    return {"success": True, "inserted": count}


@router.post("/api/rag/greprag/query")
def greprag_query(payload: GrepRAGQueryRequest):
    """步骤：校验查询词 -> 调用检索问答 -> 返回答案与上下文。"""
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 GrepRAG 查询请求")
    q = (payload.query or "").strip()
    _step(trace_id, 2, "请求参数校验完成, top_k=%s, query_len=%s", payload.top_k, len(q))
    if not q:
        raise HTTPException(status_code=400, detail="query 不能为空")
    _step(trace_id, 3, "开始调用 query 执行检索")
    result = get_greprag_service().query(q, top_k=max(1, int(payload.top_k)))
    _step(trace_id, 4, "查询成功, contexts=%s", len(result.get("contexts", [])))
    return {"query": q, "top_k": max(1, int(payload.top_k)), "answer": result.get("answer", ""), "contexts": result.get("contexts", [])}


@router.get("/api/rag/greprag/docs")
def greprag_list_docs():
    """步骤：读取文档列表 -> 返回数量与详情。"""
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 GrepRAG 文档列表请求")
    docs = get_greprag_service().list_docs()
    _step(trace_id, 2, "文档列表读取成功, count=%s", len(docs))
    return {"count": len(docs), "items": docs}


@router.delete("/api/rag/greprag/docs/{doc_id}")
def greprag_delete_doc(doc_id: str):
    """步骤：校验 doc_id -> 删除文档 -> 返回删除结果。"""
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 GrepRAG 删除文档请求")
    target = (doc_id or "").strip()
    _step(trace_id, 2, "请求参数校验完成, doc_id=%s", target)
    if not target:
        raise HTTPException(status_code=400, detail="doc_id 不能为空")
    _step(trace_id, 3, "开始调用 delete_doc 执行删除")
    deleted = get_greprag_service().delete_doc(target)
    if not deleted:
        _step(trace_id, 4, "删除失败, 原因=文档不存在, doc_id=%s", target)
        raise HTTPException(status_code=404, detail="doc_id 不存在")
    _step(trace_id, 4, "删除成功, doc_id=%s", target)
    return {"success": True, "doc_id": target}


@router.get("/api/rag/greprag/config")
def greprag_config():
    """步骤：读取当前 GrepRAG 配置并返回。"""
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 GrepRAG 配置查询请求")
    cfg = get_greprag_service().config()
    _step(trace_id, 2, "配置查询成功, docs_dir=%s", cfg.get("docs_dir", ""))
    return cfg


@router.post("/api/rag/greprag/reindex")
def greprag_reindex(payload: GrepRAGReindexRequest):
    """步骤：按目录重建索引 -> 返回加载数量与路径配置。"""
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 GrepRAG 重建索引请求")
    _step(trace_id, 2, "请求参数校验完成, clear_existing=%s", bool(payload.clear_existing))
    _step(trace_id, 3, "开始调用 rebuild_from_docs_dir 执行重建")
    loaded = get_greprag_service().rebuild_from_docs_dir(clear_existing=bool(payload.clear_existing))
    cfg = get_greprag_service().config()
    _step(trace_id, 4, "重建索引成功, loaded=%s, doc_count=%s", loaded, cfg.get("doc_count", 0))
    return {
        "success": True,
        "loaded": loaded,
        "clear_existing": bool(payload.clear_existing),
        "docs_dir": cfg.get("docs_dir", ""),
        "db_path": cfg.get("db_path", ""),
        "doc_count": cfg.get("doc_count", 0),
    }


@router.post("/api/rag/greprag/text-to-md")
def greprag_text_to_md(payload: GrepRAGTextToMdRequest):
    """步骤：校验参数 -> 写入 Markdown -> 返回文件路径。"""
    trace_id = uuid.uuid4().hex[:8]
    _step(trace_id, 1, "收到 GrepRAG 文本转 Markdown 请求")
    filename = (payload.filename or "").strip()
    text = payload.text or ""
    _step(trace_id, 2, "请求参数校验完成, filename=%s, text_len=%s", filename, len(text))
    if not filename:
        raise HTTPException(status_code=400, detail="filename 不能为空")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")
    try:
        _step(trace_id, 3, "开始调用 text_to_markdown_file 创建文件")
        file_path = get_greprag_service().text_to_markdown_file(filename, text)
        _step(trace_id, 4, "文本转 Markdown 成功, file_path=%s", file_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"创建 Markdown 文件失败: {exc}") from exc
    return {"success": True, "filename": filename, "file_path": file_path}
