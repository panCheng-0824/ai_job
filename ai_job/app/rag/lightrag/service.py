"""LightRAG 核心服务：初始化、写入、查询与图谱操作。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import weakref
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

from .config import LightRAGConfig, load_lightrag_config_from_env, resolve_lightrag_working_dir
from .doc_clean import llm_clean_documents
from .initializer import initialize_rag_instance
from .runtime import (
    LightRAGUnavailableError,
    load_light_rag_symbols,
)
from .trace import new_op_id, step

_RAG_SINGLETON: "LightRAGService | None" = None
_RAG_BY_LOOP: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, LightRAGService]" = (
    weakref.WeakKeyDictionary()
)
_RAG_LOCK = Lock()
log = logging.getLogger(__name__)


class LightRAGService:
    """面向接口层的 LightRAG 状态服务。"""

    def __init__(self, config: LightRAGConfig):
        self._config = config
        self._rag: Any | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    def storage_info(self) -> dict[str, str]:
        return {
            "graph_storage": self._config.graph_storage,
            "vector_storage": self._config.vector_storage,
        }

    async def _ensure_ready(self) -> None:
        if self._initialized and self._rag is not None:
            return
        async with self._init_lock:
            if self._initialized and self._rag is not None:
                return
            op_id = new_op_id("init")
            step(log, op_id, 1, "ensure_ready 开始执行初始化检查")
            try:
                self._rag = await initialize_rag_instance(self._config, op_id)
                self._initialized = True
                step(log, op_id, 8, "ensure_ready 执行成功")
            except Exception:
                log.exception("LightRAG 初始化失败, op_id=%s", op_id)
                step(log, op_id, 8, "ensure_ready 执行失败")
                raise

    async def _call_rag_method(self, method_names: list[str], *args: Any, **kwargs: Any) -> Any:
        await self._ensure_ready()
        assert self._rag is not None
        for name in method_names:
            fn = getattr(self._rag, name, None)
            if fn is None:
                continue
            started = time.perf_counter()
            try:
                if asyncio.iscoroutinefunction(fn):
                    result = await fn(*args, **kwargs)
                else:
                    result = fn(*args, **kwargs)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                log.info("LightRAG 底层方法调用成功, method=%s, elapsedMs=%s", name, elapsed_ms)
                return result
            except Exception:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                log.exception("LightRAG 底层方法调用失败, method=%s, elapsedMs=%s", name, elapsed_ms)
                raise
        raise AttributeError(f"LightRAG 方法不存在: {method_names}")

    async def _get_processing_status_counts(self) -> dict[str, int]:
        """读取 LightRAG 文档处理状态计数，失败时返回空字典。"""
        assert self._rag is not None
        fn = getattr(self._rag, "get_processing_status", None)
        if fn is None:
            return {}
        try:
            result = await fn() if asyncio.iscoroutinefunction(fn) else fn()
            if isinstance(result, dict):
                return {str(k).lower(): int(v) for k, v in result.items()}
        except Exception:
            log.exception("LightRAG 读取处理状态统计失败")
        return {}

    async def _get_doc_statuses(
        self, docs: list[str], explicit_doc_ids: list[str] | None = None
    ) -> dict[str, str]:
        """查询文档处理状态；若传入 explicit_doc_ids 则按该 id 列表查，否则按正文 hash。"""
        details = await self._get_doc_status_details(docs, explicit_doc_ids=explicit_doc_ids)
        return {doc_id: item.get("status", "") for doc_id, item in details.items()}

    @staticmethod
    def _normalize_doc_status(status: Any) -> str:
        """规范化状态值，兼容 Enum 字符串形式。"""
        normalized = str(status or "").strip().lower()
        if "." in normalized:
            normalized = normalized.split(".")[-1]
        return normalized

    @staticmethod
    def _extract_status_error_from_row(row: Any) -> tuple[str, str]:
        """从 LightRAG doc_status 条目提取 status 与 error（兼容 error_msg 字段）。"""
        if isinstance(row, dict):
            status = LightRAGService._normalize_doc_status(row.get("status", ""))
            error = str(
                row.get("error_msg")
                or row.get("error")
                or row.get("message")
                or ""
            ).strip()
            return status, error
        if row is not None:
            status = LightRAGService._normalize_doc_status(getattr(row, "status", ""))
            error = str(
                getattr(row, "error_msg", "")
                or getattr(row, "error", "")
                or getattr(row, "message", "")
                or ""
            ).strip()
            return status, error
        return "", ""

    def _read_disk_doc_status_rows(self, doc_ids: list[str]) -> dict[str, dict[str, str]]:
        """从磁盘 kv_store_doc_status JSON 读取状态（API 未返回 error 时兜底）。"""
        if not doc_ids:
            return {}
        wanted = set(doc_ids)
        found: dict[str, dict[str, str]] = {}
        cfg_root = Path(self._config.working_dir).expanduser().resolve()
        for path in sorted({p for p in cfg_root.rglob("kv_store_*doc_status*.json") if p.is_file()}):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            for doc_id in list(wanted):
                if doc_id in found:
                    continue
                row = raw.get(doc_id)
                if not isinstance(row, dict):
                    continue
                status, error = self._extract_status_error_from_row(row)
                if status or error:
                    found[doc_id] = {"status": status, "error": error}
            if len(found) >= len(wanted):
                break
        return found

    async def _get_doc_status_details(
        self, docs: list[str], explicit_doc_ids: list[str] | None = None
    ) -> dict[str, dict[str, str]]:
        """查询文档处理状态详情。explicit_doc_ids 与 ainsert 传入的 ids 一致时使用，否则按正文 md5 计算 doc- id。"""
        assert self._rag is not None
        if not docs:
            return {}
        try:
            from lightrag.utils import compute_mdhash_id

            if explicit_doc_ids is not None:
                doc_ids = list(explicit_doc_ids)
            else:
                doc_ids = [compute_mdhash_id(content, prefix="doc-") for content in docs]
            fn = getattr(self._rag, "aget_docs_by_ids", None)
            raw: dict[Any, Any] = {}
            if fn is not None:
                raw = await fn(doc_ids) if asyncio.iscoroutinefunction(fn) else fn(doc_ids)
                if not isinstance(raw, dict):
                    raw = {}
            disk_rows = self._read_disk_doc_status_rows(doc_ids)
            out: dict[str, dict[str, str]] = {}
            for doc_id in doc_ids:
                item = raw.get(doc_id)
                status, error = self._extract_status_error_from_row(item)
                if not status and not error:
                    disk_item = disk_rows.get(doc_id, {})
                    status = disk_item.get("status", "")
                    error = disk_item.get("error", "")
                elif not error:
                    error = disk_rows.get(doc_id, {}).get("error", "")
                if status or error:
                    out[doc_id] = {
                        "status": status,
                        "error": error,
                    }
            return out
        except Exception:
            log.exception("LightRAG 按文档读取处理状态失败")
            return {}

    @staticmethod
    def _strip_docs(texts: Iterable[str]) -> list[str]:
        """基础清洗：去空白与空串。"""
        return [t.strip() for t in texts if t and t.strip()]

    @staticmethod
    def _doc_ids_for_status_check(docs: list[str], explicit_doc_ids: list[str] | None) -> list[str]:
        """与 _get_doc_status_details 使用相同的文档 id 列表，供轮询终态校验。"""
        from lightrag.utils import compute_mdhash_id

        if explicit_doc_ids is not None:
            return list(explicit_doc_ids)
        return [compute_mdhash_id(content, prefix="doc-") for content in docs]

    async def _await_docs_terminal_status(
        self,
        op_id: str,
        docs: list[str],
        explicit_doc_ids: list[str] | None,
        doc_ids: list[str],
    ) -> None:
        """
        写入后 LightRAG 对文档的处理是异步的：可能长时间处于 pending / processing。
        批量同步场景下不能把「尚未处理完」直接当成错误，须等到终态（processed 或 failed）或超时。

        环境变量（可选）：
        - LIGHTRAG_INSERT_STATUS_WAIT_TIMEOUT_SEC：最长等待秒数，默认 600。
        - LIGHTRAG_INSERT_STATUS_POLL_INTERVAL_SEC：轮询间隔秒，默认 0.5。
        """
        timeout_sec = float(os.getenv("LIGHTRAG_INSERT_STATUS_WAIT_TIMEOUT_SEC", "600") or "600")
        interval_sec = float(os.getenv("LIGHTRAG_INSERT_STATUS_POLL_INTERVAL_SEC", "0.5") or "0.5")
        timeout_sec = max(5.0, timeout_sec)
        interval_sec = max(0.1, min(interval_sec, 30.0))
        deadline = time.monotonic() + timeout_sec
        last_details: dict[str, dict[str, str]] = {}
        poll_started = time.monotonic()

        while time.monotonic() < deadline:
            last_details = await self._get_doc_status_details(docs, explicit_doc_ids=explicit_doc_ids)
            failed: dict[str, dict[str, str]] = {}
            pending_like: list[str] = []

            for doc_id in doc_ids:
                item = last_details.get(doc_id)
                if item is None:
                    pending_like.append(doc_id)
                    continue
                st = (item.get("status") or "").strip().lower()
                if st == "processed":
                    continue
                if st == "failed":
                    failed[doc_id] = item
                elif st in ("pending", "processing", ""):
                    pending_like.append(doc_id)
                else:
                    err = (item.get("error") or item.get("message") or "").strip() or f"未知状态: {st}"
                    failed[doc_id] = {**item, "error": err}

            if failed:
                detail = {}
                for k, v in failed.items():
                    err = (v.get("error") or "").strip()
                    if not err:
                        err = "LightRAG 未返回具体原因（常见：LLM 实体抽取失败、Neo4j/Milvus 写入异常；请查 ai_job 日志）"
                    detail[k] = {"status": v.get("status", ""), "error": err}
                raise RuntimeError("LightRAG 文档处理失败（明确失败）: " + str(detail))

            if not pending_like:
                step(
                    log,
                    op_id,
                    9,
                    "写入后文档均已达到终态 processed, docCount=%s, details=%s",
                    len(doc_ids),
                    {k: v.get("status") for k, v in last_details.items()},
                )
                return

            step(
                log,
                op_id,
                9,
                "LightRAG 文档处理中, pendingOrProcessing=%s, pollIntervalSec=%s, waitedSec=%.1f",
                pending_like,
                interval_sec,
                time.monotonic() - poll_started,
            )
            await asyncio.sleep(interval_sec)

        raise RuntimeError(
            "LightRAG 等待文档处理超时（未在限定时间内变为成功或明确失败）。"
            f"timeout_sec={timeout_sec}, doc_ids={doc_ids}, last_status={last_details}"
        )

    async def _validate_insert_result(
        self,
        op_id: str,
        docs: list[str],
        before_counts: dict[str, int],
        explicit_doc_ids: list[str] | None = None,
    ) -> None:
        step(log, op_id, 8, "写入后按文档 id 轮询直至 processed / failed 或超时")
        doc_ids = self._doc_ids_for_status_check(docs, explicit_doc_ids)
        if doc_ids:
            await self._await_docs_terminal_status(op_id, docs, explicit_doc_ids, doc_ids)

        step(log, op_id, 10, "写入后读取处理状态统计")
        after_counts = await self._get_processing_status_counts()
        failed_increase = after_counts.get("failed", 0) - before_counts.get("failed", 0)
        processed_increase = after_counts.get("processed", 0) - before_counts.get("processed", 0)
        step(
            log,
            op_id,
            11,
            "写入增量统计, processed_delta=%s, failed_delta=%s, before=%s, after=%s",
            processed_increase,
            failed_increase,
            before_counts,
            after_counts,
        )
        # LightRAG 某些版本在内部吞掉单文档异常，这里做一层状态校验，避免“假成功”。
        if failed_increase > 0 or processed_increase < len(docs):
            raise RuntimeError(
                "LightRAG 写入未完成。"
                f"processed_delta={processed_increase}, failed_delta={failed_increase}, "
                f"before={before_counts}, after={after_counts}"
            )

    @staticmethod
    def _normalize_job_doc_ids(job_ids: list[str]) -> list[str]:
        """将业务岗位 id 规范为 LightRAG 文档 id（稳定、可读）。"""
        out: list[str] = []
        for raw in job_ids:
            s = str(raw).strip()
            if not s:
                raise ValueError("job_id 不能为空")
            # 与自动 doc- 前缀区分，避免混用；UUID 等原样放在后缀
            out.append(f"job-{s}" if not s.startswith("job-") else s)
        return out

    async def insert_texts(
        self,
        texts: Iterable[str],
        job_ids: list[str] | None = None,
    ) -> tuple[int, list[str]]:
        op_id = new_op_id("insert")
        step(log, op_id, 1, "insert_texts 开始处理写入请求")
        await self._ensure_ready()
        assert self._rag is not None
        stripped = self._strip_docs(texts)
        strip_chars = sum(len(d) for d in stripped)
        step(log, op_id, 2, "基础清洗完成(strip), docCount=%s, totalChars=%s", len(stripped), strip_chars)
        lightrag_doc_ids: list[str] | None = None
        file_paths: list[str] | None = None
        if job_ids is not None:
            if len(job_ids) != len(stripped):
                raise ValueError(
                    f"job_ids 条数({len(job_ids)})与 strip 后文档条数({len(stripped)})不一致，请与有效 texts 一一对应"
                )
            trimmed_jids = [str(x).strip() for x in job_ids]
            if any(not x for x in trimmed_jids):
                raise ValueError("job_id 不能为空")
            if len(trimmed_jids) != len(set(trimmed_jids)):
                raise ValueError("job_ids 存在重复")
            lightrag_doc_ids = self._normalize_job_doc_ids(trimmed_jids)
            file_paths = [f"{doc_id}.md" for doc_id in lightrag_doc_ids]
            log.info(
                "LightRAG 写入将使用业务文档 id, op_id=%s, upload_ids=%s",
                op_id,
                lightrag_doc_ids,
            )
        docs = await llm_clean_documents(stripped, self._config.model_level, op_id)
        total_chars = sum(len(d) for d in docs)
        step(log, op_id, 3, "文档清洗流水线结束, docCount=%s, totalChars=%s", len(docs), total_chars)
        if docs:
            preview = docs[0][:180]
            step(log, op_id, 4, "首条文档预览, firstDocPreview=%s", preview)
        if not docs:
            log.warning("LightRAG 写入跳过, 原因=有效文档为空")
            return 0, []
        if lightrag_doc_ids is not None and len(docs) != len(lightrag_doc_ids):
            raise ValueError("文档条数在清洗后发生变化，与 job_ids 不一致")
        started = time.perf_counter()
        log.info("LightRAG 写入开始, op_id=%s, docCount=%s, totalChars=%s", op_id, len(docs), total_chars)
        if lightrag_doc_ids is not None:
            step(log, op_id, 5, "覆盖写入：按上传 id 删除旧文档后重新入库")
            delete_fn = getattr(self._rag, "adelete_by_doc_id", None)
            if delete_fn is None:
                raise RuntimeError("当前 LightRAG 版本不支持 adelete_by_doc_id，无法实现同 id 覆盖更新")
            for doc_id in lightrag_doc_ids:
                del_result = await delete_fn(doc_id)
                status = getattr(del_result, "status", "")
                msg = getattr(del_result, "message", "")
                if status == "fail":
                    raise RuntimeError(f"删除旧文档失败, doc_id={doc_id}, detail={msg}")
                if status == "not_found":
                    log.info(
                        "LightRAG 覆盖写入：旧文档不存在跳过删除, op_id=%s, doc_id=%s",
                        op_id,
                        doc_id,
                    )
                else:
                    log.info(
                        "LightRAG 覆盖写入：已删除旧文档, op_id=%s, doc_id=%s, detail=%s",
                        op_id,
                        doc_id,
                        msg,
                    )
        step(log, op_id, 6, "写入前读取处理状态统计（用于入库后校验增量）")
        before_counts = await self._get_processing_status_counts()
        try:
            step(log, op_id, 7, "调用 ainsert 执行写入")
            if lightrag_doc_ids is not None:
                await self._rag.ainsert(docs, ids=lightrag_doc_ids, file_paths=file_paths)
            else:
                await self._rag.ainsert(docs)
            await self._validate_insert_result(
                op_id, docs, before_counts, explicit_doc_ids=lightrag_doc_ids
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            log.info("LightRAG 写入成功, op_id=%s, docCount=%s, elapsedMs=%s", op_id, len(docs), elapsed_ms)
            step(log, op_id, 12, "insert_texts 执行成功, elapsedMs=%s", elapsed_ms)
        except Exception:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            sample = docs[0][:400] if docs else ""
            log.exception(
                "LightRAG 写入失败, op_id=%s, docCount=%s, totalChars=%s, elapsedMs=%s, firstDocSample=%s",
                op_id,
                len(docs),
                total_chars,
                elapsed_ms,
                sample,
            )
            step(log, op_id, 12, "insert_texts 执行失败, elapsedMs=%s", elapsed_ms)
            raise
        return len(docs), (lightrag_doc_ids or [])

    async def query(
        self,
        question: str,
        mode: str | None = None,
        top_k: int | None = None,
        *,
        only_need_context: bool = False,
        only_need_prompt: bool = False,
    ) -> str:
        op_id = new_op_id("query")
        step(log, op_id, 1, "query 开始处理查询请求")
        await self._ensure_ready()
        assert self._rag is not None
        step(log, op_id, 2, "加载 QueryParam 符号")
        _, QueryParam, _ = load_light_rag_symbols()
        query_mode = (mode or self._config.query_mode or "mix").strip()
        query_top_k = max(1, int(top_k or self._config.top_k))
        started = time.perf_counter()
        q = question.strip()
        log.info(
            "LightRAG 查询开始, op_id=%s, mode=%s, top_k=%s, only_need_context=%s, only_need_prompt=%s, questionLength=%s",
            op_id,
            query_mode,
            query_top_k,
            only_need_context,
            only_need_prompt,
            len(q),
        )
        try:
            step(log, op_id, 3, "调用 aquery 执行检索问答")
            answer = await self._rag.aquery(
                q,
                param=QueryParam(
                    mode=query_mode,
                    top_k=query_top_k,
                    only_need_context=bool(only_need_context),
                    only_need_prompt=bool(only_need_prompt),
                ),
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            log.info("LightRAG 查询成功, op_id=%s, elapsedMs=%s, answerLength=%s", op_id, elapsed_ms, len(answer or ""))
            step(log, op_id, 4, "query 执行成功, elapsedMs=%s", elapsed_ms)
            return answer
        except Exception:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            log.exception("LightRAG 查询失败, op_id=%s, mode=%s, top_k=%s, elapsedMs=%s", op_id, query_mode, query_top_k, elapsed_ms)
            step(log, op_id, 4, "query 执行失败, elapsedMs=%s", elapsed_ms)
            raise

    async def create_entity(self, entity_name: str, data: dict[str, Any]) -> Any:
        return await self._call_rag_method(["acreate_entity", "create_entity"], entity_name, data)

    async def get_entity(self, entity_name: str) -> Any:
        return await self._call_rag_method(["aget_entity", "get_entity"], entity_name)

    async def update_entity(self, entity_name: str, data: dict[str, Any]) -> Any:
        return await self._call_rag_method(["aedit_entity", "edit_entity"], entity_name, data)

    async def delete_by_doc_id(self, doc_id: str) -> Any:
        """按文档 id 删除 LightRAG 中的岗位/文档及其关联索引。"""
        raw = str(doc_id or "").strip()
        if not raw:
            raise ValueError("doc_id 不能为空")
        await self._ensure_ready()
        assert self._rag is not None
        delete_fn = getattr(self._rag, "adelete_by_doc_id", None)
        if delete_fn is None:
            raise RuntimeError("当前 LightRAG 版本不支持 adelete_by_doc_id")
        return await delete_fn(raw)

    async def delete_entity(self, entity_name: str) -> Any:
        return await self._call_rag_method(["adelete_by_entity", "delete_by_entity"], entity_name)

    async def create_relation(self, src_id: str, tgt_id: str, data: dict[str, Any]) -> Any:
        return await self._call_rag_method(["acreate_relation", "create_relation"], src_id, tgt_id, data)

    async def get_relation(self, src_id: str, tgt_id: str) -> Any:
        return await self._call_rag_method(["aget_relation", "get_relation"], src_id, tgt_id)

    async def update_relation(self, src_id: str, tgt_id: str, data: dict[str, Any]) -> Any:
        return await self._call_rag_method(["aedit_relation", "edit_relation"], src_id, tgt_id, data)

    async def delete_relation(self, src_id: str, tgt_id: str) -> Any:
        return await self._call_rag_method(["adelete_by_relation", "delete_by_relation"], src_id, tgt_id)

    def _aggregate_disk_doc_status_counts(self) -> dict[str, int]:
        """扫描 working_dir 下所有 kv_store doc_status，按 doc_id 去重统计各状态数量。"""
        counts: dict[str, int] = {"pending": 0, "processing": 0, "failed": 0, "processed": 0}
        seen_doc_ids: set[str] = set()
        cfg_root = Path(self._config.working_dir).expanduser().resolve()
        paths = sorted({p for p in cfg_root.rglob("kv_store_*doc_status*.json") if p.is_file()})
        for path in paths:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                log.warning("读取 doc_status 统计失败, path=%s", path, exc_info=True)
                continue
            if not isinstance(raw, dict):
                continue
            for doc_id, row in raw.items():
                doc_key = str(doc_id).strip()
                if not doc_key or doc_key in seen_doc_ids or not isinstance(row, dict):
                    continue
                seen_doc_ids.add(doc_key)
                st = self._normalize_doc_status(row.get("status", ""))
                if st in counts:
                    counts[st] += 1
                elif st:
                    counts[st] = counts.get(st, 0) + 1
        return counts

    async def get_backlog_stats(self) -> dict[str, Any]:
        """
        返回 LightRAG 文档积压统计（pending / processing / failed 及 processed 总量）。
        内存与磁盘取各桶最大值，与清理积压逻辑一致。
        """
        disk = self._aggregate_disk_doc_status_counts()
        memory: dict[str, int] = {"pending": 0, "processing": 0, "failed": 0, "processed": 0}
        memory_available = False
        storage: dict[str, Any] = {}
        try:
            await self._ensure_ready()
            assert self._rag is not None
            from lightrag.base import DocStatus

            rag = self._rag
            pending, processing, failed, status_counts = await asyncio.gather(
                rag.get_docs_by_status(DocStatus.PENDING),
                rag.get_docs_by_status(DocStatus.PROCESSING),
                rag.get_docs_by_status(DocStatus.FAILED),
                self._get_processing_status_counts(),
            )
            memory = {
                "pending": len(pending),
                "processing": len(processing),
                "failed": len(failed),
                "processed": int(status_counts.get("processed", 0)),
            }
            memory_available = True
            storage = self.storage_info()
        except Exception as exc:
            log.warning("LightRAG 内存积压统计不可用, 仅返回磁盘统计, reason=%s", exc)

        pending = max(memory["pending"], disk.get("pending", 0))
        processing = max(memory["processing"], disk.get("processing", 0))
        failed = max(memory["failed"], disk.get("failed", 0))
        processed = max(memory.get("processed", 0), disk.get("processed", 0))
        return {
            "pending": pending,
            "processing": processing,
            "failed": failed,
            "processed": processed,
            "backlog_total": pending + processing + failed,
            "memory_available": memory_available,
            "from_memory": memory if memory_available else None,
            "from_disk": disk,
            **storage,
        }

    async def delete_non_processed_documents(
        self,
        *,
        dry_run: bool = False,
        merge_disk_doc_status: bool = True,
        max_concurrent_deletes: int = 1,
        strip_non_processed_from_disk_doc_status: bool = True,
    ) -> dict[str, Any]:
        """
        删除文档状态中「未成功完成」的文档及其关联数据（分片、向量、图谱等）。

        覆盖状态：pending、processing、failed。processed 不会被删除。

        默认通过 LightRAG 的 ``adelete_by_doc_id`` 删除，与只手改 ``kv_store_*.json`` 相比，
        能尽量保持图存储与向量库一致。

        若 ``merge_disk_doc_status=True``，会额外扫描工作目录下 ``kv_store_*doc_status*.json``，
        把其中 ``status != processed`` 的 doc_id 并入待删列表（用于与内存状态偶发不同步时兜底）。

        Args:
            dry_run: 为 True 时只统计待删 doc_id，不执行删除。
            merge_disk_doc_status: 是否合并磁盘上 doc_status JSON 中的非 processed 条目。
            max_concurrent_deletes: 并发删除上限，避免压垮 Neo4j / Milvus。
            strip_non_processed_from_disk_doc_status: 在 ``adelete_by_doc_id`` 结束后，对配置目录树下所有
                ``kv_store_*doc_status*.json`` 再扫一遍，删掉其中 ``status != processed`` 的条目（兜底，避免
                working_dir 与历史 JSON 路径不一致时 pending 仍留在文件里）。可能留下图/向量孤儿数据，仅适合
                「放弃未完成任务」场景。

        Returns:
            包含 candidate_doc_ids、按 doc 的删除结果摘要、成功/失败计数的字典。
        """
        from lightrag.base import DocStatus

        op_id = new_op_id("purge-non-processed")
        step(log, op_id, 1, "delete_non_processed_documents 开始, dryRun=%s", dry_run)
        await self._ensure_ready()
        assert self._rag is not None
        rag = self._rag

        pending, processing, failed = await asyncio.gather(
            rag.get_docs_by_status(DocStatus.PENDING),
            rag.get_docs_by_status(DocStatus.PROCESSING),
            rag.get_docs_by_status(DocStatus.FAILED),
        )
        doc_ids: set[str] = set()
        doc_ids.update(pending.keys(), processing.keys(), failed.keys())
        step(
            log,
            op_id,
            2,
            "从 LightRAG 存储读取非终态文档, pending=%s processing=%s failed=%s",
            len(pending),
            len(processing),
            len(failed),
        )

        if merge_disk_doc_status:
            cfg_root = Path(self._config.working_dir).expanduser().resolve()
            disk_paths = sorted({p for p in cfg_root.rglob("kv_store_*doc_status*.json") if p.is_file()})
            for path in disk_paths:
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    log.warning("读取 doc_status 文件失败, path=%s", path, exc_info=True)
                    continue
                if not isinstance(raw, dict):
                    continue
                for doc_id, row in raw.items():
                    if not isinstance(row, dict):
                        continue
                    st = str(row.get("status", "")).strip().lower()
                    if st != "processed":
                        doc_ids.add(str(doc_id).strip())
            step(log, op_id, 3, "合并磁盘 doc_status 后待处理 doc_id 总数=%s", len(doc_ids))

        ordered = sorted(doc_ids)
        if dry_run:
            step(log, op_id, 8, "dry_run 结束, candidateCount=%s", len(ordered))
            return {
                "dry_run": True,
                "candidate_count": len(ordered),
                "candidate_doc_ids": ordered,
                "from_api": {
                    "pending": sorted(pending.keys()),
                    "processing": sorted(processing.keys()),
                    "failed": sorted(failed.keys()),
                },
            }

        # Neo4j 的 Single document deletion 不支持并发；串行 + 可重试错误退避，避免
        # "Deletion not allowed: current job 'Single document deletion' is not a document deletion job"。
        async def _delete_one_with_retry(doc_id: str) -> Any:
            last: Any = None
            for attempt in range(3):
                last = await rag.adelete_by_doc_id(doc_id)
                status = getattr(last, "status", "")
                if status in ("success", "not_found"):
                    return last
                msg = str(getattr(last, "message", "") or "")
                if attempt < 2 and self._is_retriable_delete_failure(msg):
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                return last
            return last

        results: list[Any] = []
        for doc_id in ordered:
            results.append(await _delete_one_with_retry(doc_id))

        successes: list[str] = []
        not_found: list[str] = []
        failures: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for doc_id, res in zip(ordered, results):
            if isinstance(res, BaseException):
                errors.append({"doc_id": doc_id, "error": f"{type(res).__name__}: {res}"})
                continue
            status = getattr(res, "status", "")
            if status == "success":
                successes.append(doc_id)
            elif status == "not_found":
                not_found.append(doc_id)
            else:
                failures.append(
                    {
                        "doc_id": doc_id,
                        "status": status,
                        "message": getattr(res, "message", ""),
                        "status_code": getattr(res, "status_code", 0),
                    }
                )

        disk_strip_report: dict[str, Any] = {}
        if strip_non_processed_from_disk_doc_status:
            cfg_root = Path(self._config.working_dir).expanduser().resolve()
            strip_paths = sorted({p for p in cfg_root.rglob("kv_store_*doc_status*.json") if p.is_file()})
            disk_strip_report = self._rewrite_disk_doc_status_remove_non_processed(strip_paths)
            step(
                log,
                op_id,
                9,
                "磁盘 doc_status 兜底清理完成, filesRewritten=%s entriesRemoved=%s",
                disk_strip_report.get("doc_status_files_rewritten", 0),
                disk_strip_report.get("doc_status_entries_removed", 0),
            )

        cfg_root = Path(self._config.working_dir).expanduser().resolve()
        strip_paths = sorted({p for p in cfg_root.rglob("kv_store_*doc_status*.json") if p.is_file()})
        remaining_non_processed = self._count_non_processed_on_disk(strip_paths)
        deep_delete_fully_cleared = len(ordered) == 0 or (
            len(failures) == 0 and len(errors) == 0 and len(successes) + len(not_found) >= len(ordered)
        )
        queue_cleared = len(ordered) == 0 or remaining_non_processed == 0

        step(
            log,
            op_id,
            8,
            "delete_non_processed_documents 完成, success=%s not_found=%s fail=%s exc=%s queue_cleared=%s",
            len(successes),
            len(not_found),
            len(failures),
            len(errors),
            queue_cleared,
        )
        return {
            "dry_run": False,
            "candidate_count": len(ordered),
            "success_count": len(successes),
            "not_found_count": len(not_found),
            "failure_count": len(failures),
            "exception_count": len(errors),
            "queue_cleared": queue_cleared,
            "remaining_non_processed_count": remaining_non_processed,
            "deep_delete_fully_cleared": deep_delete_fully_cleared,
            "success_doc_ids": successes,
            "not_found_doc_ids": not_found,
            "failures": failures,
            "errors": errors,
            "disk_strip": disk_strip_report,
        }

    @staticmethod
    def _count_non_processed_on_disk(paths: list[Path]) -> int:
        count = 0
        for path in paths:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            for row in raw.values():
                if isinstance(row, dict) and str(row.get("status", "")).strip().lower() != "processed":
                    count += 1
        return count

    @staticmethod
    def _is_retriable_delete_failure(message: str) -> bool:
        m = (message or "").lower()
        return "deletion not allowed" in m or "single document deletion" in m

    @staticmethod
    def _rewrite_disk_doc_status_remove_non_processed(paths: list[Path]) -> dict[str, Any]:
        """从磁盘上的 doc_status JSON 中移除非 processed 条目（不经过 LightRAG 存储层）。"""
        files_rewritten = 0
        entries_removed = 0
        for path in paths:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                log.warning("disk_strip 读取失败, path=%s", path, exc_info=True)
                continue
            if not isinstance(raw, dict):
                continue
            kept: dict[str, Any] = {}
            for k, v in raw.items():
                if isinstance(v, dict) and str(v.get("status", "")).strip().lower() == "processed":
                    kept[k] = v
            removed = len(raw) - len(kept)
            if removed <= 0:
                continue
            path.write_text(json.dumps(kept, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            files_rewritten += 1
            entries_removed += removed
        return {
            "doc_status_files_rewritten": files_rewritten,
            "doc_status_entries_removed": entries_removed,
        }


def get_lightrag_service() -> LightRAGService:
    """
    获取 LightRAG 服务实例。

    按「当前 running 事件循环」缓存一份实例，避免 PriorityQueue 绑定到 A 循环却在 B 循环使用。
    无 running loop 时（脚本/同步入口）回退到进程级单例。
    """
    global _RAG_SINGLETON
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        svc = _RAG_BY_LOOP.get(loop)
        if svc is not None:
            return svc
        with _RAG_LOCK:
            svc = _RAG_BY_LOOP.get(loop)
            if svc is None:
                cfg = load_lightrag_config_from_env()
                log.info("创建 LightRAG 服务实例(按事件循环), loop_id=%s, config=%s", id(loop), cfg)
                svc = LightRAGService(cfg)
                _RAG_BY_LOOP[loop] = svc
        return svc

    if _RAG_SINGLETON is not None:
        return _RAG_SINGLETON
    with _RAG_LOCK:
        if _RAG_SINGLETON is None:
            cfg = load_lightrag_config_from_env()
            log.info("创建 LightRAG 服务单例(无 running loop), config=%s", cfg)
            _RAG_SINGLETON = LightRAGService(cfg)
    return _RAG_SINGLETON
