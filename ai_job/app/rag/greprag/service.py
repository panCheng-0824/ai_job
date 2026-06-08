"""GrepRAG 服务：基于本地文本的轻量检索实现。"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List

from app.common.runtime_config import load_runtime_config

log = logging.getLogger(__name__)


def _step(op_id: str, step_no: int, message: str, *args) -> None:
    """输出带顺序号的原子步骤日志。"""
    log.info("[op=%s][step=%02d] " + message, op_id, step_no, *args)


@dataclass
class GrepRAGDocument:
    """文档记录结构。"""

    doc_id: str
    content: str
    source: str
    created_at: str
    file_path: str = ""


class GrepRAGService:
    """GrepRAG 核心服务，负责文档持久化与检索。"""

    def __init__(self, docs_dir: Path, db_path: Path) -> None:
        """步骤：初始化内存索引 -> 准备本地存储 -> 从磁盘加载历史文档。"""
        self._docs: Dict[str, GrepRAGDocument] = {}
        self._lock = Lock()
        self._docs_dir = docs_dir
        self._db_path = db_path
        self._prepare_storage()
        self._load_from_disk()

    def _prepare_storage(self) -> None:
        """步骤：创建目录 -> 初始化 db 文件。"""
        op_id = "prepare-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "prepare storage start")
        self._docs_dir.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._db_path.exists():
            self._db_path.write_text("[]", encoding="utf-8")
            _step(op_id, 2, "created db file=%s", self._db_path)
        else:
            _step(op_id, 2, "db file already exists=%s", self._db_path)
        log.info("GrepRAG 存储准备完成, docs_dir=%s, db_path=%s", self._docs_dir, self._db_path)

    def _load_from_disk(self) -> None:
        """步骤：读取 JSON -> 校验记录 -> 回填内存索引。"""
        op_id = "load-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "load from disk start")
        try:
            arr = json.loads(self._db_path.read_text(encoding="utf-8"))
            if not isinstance(arr, list):
                log.warning("GrepRAG 数据库文件结构异常(非列表), path=%s", self._db_path)
                return
        except Exception:
            log.exception("GrepRAG 加载数据库文件失败, path=%s", self._db_path)
            return
        with self._lock:
            self._docs = {}
            for item in arr:
                if not isinstance(item, dict):
                    continue
                doc_id = str(item.get("doc_id", "")).strip()
                content = str(item.get("content", "")).strip()
                if not doc_id or not content:
                    continue
                self._docs[doc_id] = GrepRAGDocument(
                    doc_id=doc_id,
                    content=content,
                    source=str(item.get("source", "manual")),
                    created_at=str(item.get("created_at", datetime.utcnow().isoformat() + "Z")),
                    file_path=str(item.get("file_path", "")),
                )
        _step(op_id, 2, "load from disk complete, doc_count=%s", len(self._docs))
        log.info("GrepRAG 磁盘加载完成, doc_count=%s", len(self._docs))

    def _save_to_disk(self) -> None:
        """步骤：序列化内存索引 -> 覆盖写入 JSON 文件。"""
        op_id = "save-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "save to disk start")
        with self._lock:
            payload = [
                {
                    "doc_id": d.doc_id,
                    "content": d.content,
                    "source": d.source,
                    "created_at": d.created_at,
                    "file_path": d.file_path,
                }
                for d in self._docs.values()
            ]
        self._db_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        _step(op_id, 2, "save to disk complete, doc_count=%s", len(payload))
        log.info("GrepRAG 持久化保存完成, doc_count=%s", len(payload))

    def config(self) -> dict:
        """返回当前存储路径与文档数量。"""
        return {"docs_dir": str(self._docs_dir), "db_path": str(self._db_path), "doc_count": len(self._docs)}

    def text_to_markdown_file(self, filename: str, text: str) -> str:
        """步骤：校验参数 -> 清洗文件名 -> 写入 Markdown 文件。"""
        op_id = "to-md-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "text_to_markdown_file start")
        name = (filename or "").strip()
        body = (text or "").strip()
        log.info("GrepRAG 创建 Markdown 请求, raw_filename=%s, text_len=%s", name, len(body))
        if not name:
            raise ValueError("filename 不能为空")
        if not body:
            raise ValueError("text 不能为空")
        # 保留中文与常规 Unicode 字符，仅替换文件系统非法字符。
        safe = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
        if not safe.lower().endswith(".md"):
            safe = safe + ".md"
        safe = safe.strip(" .")
        if safe in {".md", "..md"}:
            raise ValueError("filename 非法")
        if not safe:
            raise ValueError("filename 非法")

        # 文件名约定: <base>_<timestamp>.md，仅在同 base 下保留时间戳最新文件。
        stem = Path(safe).stem
        ts_match = re.match(r"^(?P<base>.+)_(?P<ts>\d{10,17})$", stem)
        if ts_match:
            base = ts_match.group("base")
            new_ts = int(ts_match.group("ts"))
            keep_new = True
            removed_files: List[str] = []
            for old_path in self._docs_dir.glob(f"{base}_*.md"):
                old_match = re.match(rf"^{re.escape(base)}_(\d{{10,17}})$", old_path.stem)
                if not old_match:
                    continue
                old_ts = int(old_match.group(1))
                if old_ts > new_ts:
                    # 现有文件更新，保留旧文件并直接返回。
                    keep_new = False
                    safe = old_path.name
                    log.info(
                        "GrepRAG 跳过写入旧版本文件, base=%s, incoming_ts=%s, existing_file=%s, existing_ts=%s",
                        base,
                        new_ts,
                        old_path.name,
                        old_ts,
                    )
                    break
                if old_ts <= new_ts:
                    old_path.unlink(missing_ok=True)
                    removed_files.append(old_path.name)
            if keep_new:
                safe = f"{base}_{new_ts}.md"
                if removed_files:
                    log.info(
                        "GrepRAG 删除旧版本文件完成, base=%s, incoming_ts=%s, removed=%s",
                        base,
                        new_ts,
                        removed_files,
                    )
        target = self._docs_dir / safe
        if not target.exists():
            target.write_text(body + "\n", encoding="utf-8")
            log.info("GrepRAG Markdown 文件创建成功, file=%s, text_len=%s", target, len(body))
        else:
            log.info("GrepRAG Markdown 文件已存在，跳过覆盖写入, file=%s", target)
        _step(op_id, 2, "text_to_markdown_file success, file=%s", target)
        log.info("GrepRAG 文本写入 Markdown 完成, file=%s", target)
        return str(target)

    def delete_markdown_file(self, file_path: str) -> bool:
        """删除 docs 目录下的 Markdown 文件，并清理内存索引中同路径条目。"""
        op_id = "del-md-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "delete_markdown_file start")
        raw = (file_path or "").strip()
        if not raw:
            return False
        target = Path(raw).expanduser().resolve()
        docs_root = self._docs_dir.resolve()
        if docs_root not in target.parents and target != docs_root:
            log.warning("GrepRAG 删除 Markdown 拒绝越界路径, file=%s, docs_dir=%s", target, docs_root)
            return False
        removed_file = False
        if target.is_file():
            target.unlink(missing_ok=True)
            removed_file = True
        removed_docs = 0
        with self._lock:
            stale_ids = [doc_id for doc_id, doc in self._docs.items() if doc.file_path and Path(doc.file_path).resolve() == target]
            for doc_id in stale_ids:
                self._docs.pop(doc_id, None)
                removed_docs += 1
            if removed_docs:
                self._save_to_disk()
        _step(op_id, 2, "delete_markdown_file done, removed_file=%s, removed_docs=%s", removed_file, removed_docs)
        log.info("GrepRAG 删除 Markdown 完成, file=%s, removed_file=%s, removed_docs=%s", target, removed_file, removed_docs)
        return removed_file or removed_docs > 0

    def insert_texts(self, texts: List[str], source: str = "manual") -> int:
        """步骤：清洗输入 -> 生成 doc_id -> 入内存并持久化。"""
        op_id = "insert-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "insert_texts start")
        cleaned = [str(t).strip() for t in texts if str(t).strip()]
        log.info(
            "GrepRAG 写入请求, source=%s, input_count=%s, valid_count=%s",
            source,
            len(texts),
            len(cleaned),
        )
        if not cleaned:
            log.warning("GrepRAG 写入跳过, 原因=有效文本为空")
            return 0
        now = datetime.utcnow().isoformat() + "Z"
        _step(op_id, 2, "clean texts complete, count=%s", len(cleaned))
        with self._lock:
            for text in cleaned:
                doc_id = "grepdoc-" + uuid.uuid4().hex[:12]
                log.info("GrepRAG 写入单条文档, doc_id=%s, source=%s, content_len=%s", doc_id, source, len(text))
                self._docs[doc_id] = GrepRAGDocument(doc_id=doc_id, content=text, source=source, created_at=now, file_path="")
        _step(op_id, 3, "memory upsert complete")
        self._save_to_disk()
        _step(op_id, 4, "insert_texts success, inserted=%s", len(cleaned))
        log.info("GrepRAG 写入成功, inserted=%s, source=%s", len(cleaned), source)
        return len(cleaned)

    def rebuild_from_docs_dir(self, *, clear_existing: bool = False) -> int:
        """步骤：扫描目录 -> 可选清空 -> 批量重建索引 -> 持久化。"""
        op_id = "rebuild-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "rebuild_from_docs_dir start, clear_existing=%s", clear_existing)
        patterns = ("*.txt", "*.md", "*.markdown", "*.json")
        files: List[Path] = []
        for pat in patterns:
            files.extend(self._docs_dir.glob(pat))
        log.info("GrepRAG 重建扫描完成, file_count=%s", len(files))
        _step(op_id, 2, "scan complete, file_count=%s", len(files))
        loaded = 0
        if clear_existing:
            with self._lock:
                self._docs = {}
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            for path in files:
                try:
                    content = path.read_text(encoding="utf-8").strip()
                except Exception:
                    continue
                if not content:
                    continue
                doc_id = "grepdoc-" + uuid.uuid4().hex[:12]
                self._docs[doc_id] = GrepRAGDocument(
                    doc_id=doc_id,
                    content=content,
                    source="docs_dir",
                    created_at=now,
                    file_path=str(path),
                )
                loaded += 1
        self._save_to_disk()
        _step(op_id, 3, "rebuild success, loaded=%s", loaded)
        log.info("GrepRAG 重建索引成功, loaded=%s, clear_existing=%s", loaded, clear_existing)
        return loaded

    def list_docs(self) -> List[dict]:
        """步骤：读取内存索引 -> 按创建时间倒序返回。"""
        op_id = "list-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "list_docs start")
        with self._lock:
            items = list(self._docs.values())
        items.sort(key=lambda x: x.created_at, reverse=True)
        _step(op_id, 2, "list_docs success, count=%s", len(items))
        return [{"doc_id": item.doc_id, "source": item.source, "created_at": item.created_at, "content_preview": item.content[:160], "file_path": item.file_path} for item in items]

    def delete_doc(self, doc_id: str) -> bool:
        """步骤：删除内存记录 -> 若成功则持久化。"""
        op_id = "delete-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "delete_doc start, doc_id=%s", doc_id)
        with self._lock:
            deleted = self._docs.pop(doc_id, None) is not None
        if deleted:
            self._save_to_disk()
            _step(op_id, 2, "delete_doc success")
            log.info("GrepRAG delete doc success, doc_id=%s", doc_id)
        else:
            _step(op_id, 2, "delete_doc missed")
            log.warning("GrepRAG 删除文档未命中, doc_id=%s", doc_id)
        return deleted

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """步骤：构建关键词 -> 计算命中分数 -> 按分数截断返回。"""
        op_id = "search-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "search start")
        q = (query or "").strip()
        if not q:
            log.warning("GrepRAG search skipped, empty query")
            return []
        pattern = re.compile(re.escape(q), re.IGNORECASE)
        tokens = [t for t in re.split(r"\s+", q) if t]
        with self._lock:
            docs = list(self._docs.values())
        ranked: List[tuple[int, GrepRAGDocument]] = []
        for doc in docs:
            exact_hits = len(pattern.findall(doc.content))
            token_hits = 0 if exact_hits > 0 else sum(doc.content.lower().count(t.lower()) for t in tokens)
            score = exact_hits * 3 + token_hits
            if score > 0:
                ranked.append((score, doc))
        ranked.sort(key=lambda x: x[0], reverse=True)
        out: List[dict] = []
        for score, doc in ranked[: max(1, int(top_k))]:
            out.append({"doc_id": doc.doc_id, "source": doc.source, "score": score, "content": doc.content, "file_path": doc.file_path})
        _step(op_id, 2, "search success, hit_count=%s", len(out))
        log.info("GrepRAG 检索完成, query=%s, hit_count=%s", q, len(out))
        return out

    def query(self, query: str, top_k: int = 5) -> dict:
        """步骤：执行检索 -> 命中为空返回提示 -> 否则拼接回答。"""
        op_id = "query-" + uuid.uuid4().hex[:8]
        _step(op_id, 1, "query start")
        hits = self.search(query, top_k=top_k)
        if not hits:
            _step(op_id, 2, "query no hits")
            log.info("GrepRAG 查询无命中, query=%s", query)
            return {"answer": "未检索到相关内容，请先插入语料或调整关键词。", "contexts": []}
        answer = "\n\n".join([f"[{i + 1}] {x['content']}" for i, x in enumerate(hits)])
        _step(op_id, 2, "query success, context_count=%s", len(hits))
        log.info("GrepRAG 查询成功, query=%s, contexts=%s", query, len(hits))
        return {"answer": answer, "contexts": hits}


_GREPRAG_SINGLETON: GrepRAGService | None = None
_GREPRAG_LOCK = Lock()


def get_greprag_service() -> GrepRAGService:
    """获取 GrepRAG 进程内单例。"""

    global _GREPRAG_SINGLETON
    if _GREPRAG_SINGLETON is not None:
        log.info("GrepRAG 单例复用命中")
        return _GREPRAG_SINGLETON
    with _GREPRAG_LOCK:
        if _GREPRAG_SINGLETON is None:
            cfg = load_runtime_config()
            base = Path(__file__).resolve().parents[3]
            docs_dir = Path(str(os.getenv("GREPRAG_DOCS_DIR", cfg.get("greprag_docs_dir", str(base / "data" / "greprag" / "docs"))))).expanduser()
            db_path = Path(str(os.getenv("GREPRAG_DB_PATH", cfg.get("greprag_db_path", str(base / "data" / "greprag" / "greprag_db.json"))))).expanduser()
            _GREPRAG_SINGLETON = GrepRAGService(docs_dir=docs_dir, db_path=db_path)
            log.info("GrepRAG 单例创建完成, docs_dir=%s, db_path=%s", docs_dir, db_path)
    return _GREPRAG_SINGLETON
