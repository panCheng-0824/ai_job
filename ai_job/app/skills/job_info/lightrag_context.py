"""LightRAG 检索上下文解析：丢弃 KG 噪音，只保留 Document Chunks 并按 job_id 去重。"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# UUID 或 32 位 hex（部分 server_job 岗位 ID）
_JOB_ID_HEX = r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}|[0-9a-fA-F]{32}"
_JOB_ID_IN_CONTENT = re.compile(rf"岗位ID[：:]\s*({_JOB_ID_HEX})")
_JOB_ID_IN_PATH = re.compile(rf"job-({_JOB_ID_HEX})(?:\.md)?", re.IGNORECASE)
_REF_LINE_RE = re.compile(r"^\[(\d+)\]\s*(.+?)\s*$", re.MULTILINE)

# LightRAG 各版本 Document Chunks 节标题
_DC_SECTION_RES = (
    re.compile(
        r"Document Chunks[^`]*```(?:json)?\s*(.*?)\s*```",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"-----Document Chunks\(DC\)-----\s*```(?:json)?\s*(.*?)\s*```",
        re.DOTALL | re.IGNORECASE,
    ),
)
_REF_SECTION_RES = (
    re.compile(
        r"Reference Document List[^`]*```\s*(.*?)\s*```",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"Reference Document List\s*(.*?)(?:\n\nDocument Chunks|\Z)",
        re.DOTALL | re.IGNORECASE,
    ),
)


def _normalize_job_id(raw: str) -> str:
    return (raw or "").strip().lower()


def extract_job_id(*, content: str, file_path: str = "") -> str:
    """从正文「岗位ID：」或 file_path（job-<id>.md）提取业务 job_id。"""
    m = _JOB_ID_IN_CONTENT.search(content or "")
    if m:
        return _normalize_job_id(m.group(1))
    fp = (file_path or "").strip()
    m = _JOB_ID_IN_PATH.search(fp)
    if m:
        return _normalize_job_id(m.group(1))
    return ""


def parse_reference_document_list(context_text: str) -> Dict[str, str]:
    """
    解析 Reference Document List，返回 reference_id -> job_id。

    示例::

        [5] job-d99d05fe282741c9b3d276b666a59290.md
    """
    text = (context_text or "").strip()
    if not text:
        return {}
    body = ""
    for pat in _REF_SECTION_RES:
        m = pat.search(text)
        if m:
            body = m.group(1).strip()
            break
    if not body:
        # 无独立节时，在全文中查找 [n] job-xxx.md 行
        body = text

    out: Dict[str, str] = {}
    for ref_id, path in _REF_LINE_RE.findall(body):
        jid = extract_job_id(content="", file_path=path)
        if jid:
            out[str(ref_id).strip()] = jid
    return out


def _parse_chunk_records(raw: str) -> List[Dict[str, Any]]:
    """解析 Document Chunks 块：支持 JSON 数组或 JSONL（每行一个对象）。"""
    body = (raw or "").strip()
    if not body:
        return []

    # JSON 数组
    try:
        data = json.loads(body)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass

    # JSONL：LightRAG 新版常见格式
    records: List[Dict[str, Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _is_document_chunk(obj: Dict[str, Any]) -> bool:
    """排除误解析进 KG 的 entity/relationship 行。"""
    if "content" not in obj:
        return False
    if "entity" in obj or "entity1" in obj:
        return False
    return bool(str(obj.get("content") or "").strip())


def parse_lightrag_document_chunks(context_text: str) -> List[Dict[str, Any]]:
    """从 LightRAG ``only_need_context`` 返回体中提取 Document Chunks。"""
    text = (context_text or "").strip()
    if not text:
        return []

    for pat in _DC_SECTION_RES:
        m = pat.search(text)
        if m:
            records = _parse_chunk_records(m.group(1))
            chunks = [x for x in records if _is_document_chunk(x)]
            if chunks:
                return chunks

    # 兜底：找含 reference_id/content 的 JSONL 块（跳过 KG entity 块）
    for block in re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE):
        records = _parse_chunk_records(block)
        chunks = [
            x
            for x in records
            if _is_document_chunk(x) and ("reference_id" in x or "file_path" in x)
        ]
        if chunks:
            return chunks
    return []


def _resolve_chunk_job_id(
    chunk: Dict[str, Any], ref_map: Dict[str, str]
) -> Tuple[str, str]:
    """合并 reference_id、file_path、正文岗位ID 得到 job_id 与文档路径。"""
    content = str(chunk.get("content") or "").strip()
    file_path = str(chunk.get("file_path") or "").strip()
    ref_id = str(chunk.get("reference_id") or "").strip()

    jid = extract_job_id(content=content, file_path=file_path)
    if not jid and ref_id:
        jid = ref_map.get(ref_id, "")
        if jid and not file_path:
            file_path = f"job-{jid}.md"
    return jid, file_path


def _looks_like_job_doc(content: str) -> bool:
    """过滤纯 KG 摘要、流程说明等无岗位结构的 chunk。"""
    text = (content or "").strip()
    if not text:
        return False
    if _JOB_ID_IN_CONTENT.search(text):
        return True
    if text.startswith("# 岗位信息") or "## 基本信息" in text[:800]:
        return True
    if "【检索摘要】" in text and "岗位ID" in text:
        return True
    return False


def dedupe_job_chunks(
    chunks: List[Dict[str, Any]], *, ref_map: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    按 job_id 去重；同一 job_id 多条 chunk 保留内容最长的一条。

    无 job_id 时仅保留形似岗位文档的 chunk，并按正文 hash 去重。
    """
    ref_map = ref_map or {}
    by_job: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    content_seen: set[str] = set()

    for chunk in chunks:
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue

        jid, file_path = _resolve_chunk_job_id(chunk, ref_map)
        has_inline_job_id = bool(_JOB_ID_IN_CONTENT.search(content))
        structured = _looks_like_job_doc(content)
        if not jid and not structured:
            continue
        # 仅靠 reference 映射、无正文岗位ID 的短片段（常见于同一 JD 被切分）直接丢弃
        if jid and not has_inline_job_id and not structured and len(content) < 300:
            continue

        content_key = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if content_key in content_seen:
            continue

        dedupe_key = jid or f"content:{content_key[:16]}"
        existing = by_job.get(dedupe_key)
        if existing is None:
            by_job[dedupe_key] = {
                "job_id": jid,
                "file_path": file_path,
                "content": content,
            }
            order.append(dedupe_key)
            content_seen.add(content_key)
            continue

        # 同一 job_id：保留更完整的正文
        if len(content) > len(str(existing.get("content") or "")):
            by_job[dedupe_key] = {
                "job_id": jid or existing.get("job_id", ""),
                "file_path": file_path or existing.get("file_path", ""),
                "content": content,
            }

    return [by_job[k] for k in order if k in by_job]


def format_deduped_job_retrieval_context(chunks: List[Dict[str, Any]]) -> str:
    """将去重后的岗位块格式化为 LLM 素材（不含 KG entity/relationship）。"""
    if not chunks:
        return ""
    lines = [f"----- 岗位素材（已按 job_id 去重，共 {len(chunks)} 条）-----", ""]
    for i, ch in enumerate(chunks, 1):
        jid = str(ch.get("job_id") or "").strip() or "未知"
        fp = str(ch.get("file_path") or "").strip()
        lines.append(f"### [{i}] job_id: {jid}")
        if fp and fp != "unknown_source":
            lines.append(f"文档: {fp}")
        lines.append("")
        lines.append(str(ch.get("content") or "").strip())
        lines.append("")
    return "\n".join(lines).strip()


def normalize_lightrag_retrieval_context(
    context_text: str,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    丢弃 Knowledge Graph 噪音，只输出 Document Chunks 经 job_id 去重后的素材。

    若无法解析任何岗位 chunk，返回空字符串（避免把 KG 实体列表喂给 LLM）。
    """
    raw = (context_text or "").strip()
    if not raw:
        return "", []

    ref_map = parse_reference_document_list(raw)
    chunks = parse_lightrag_document_chunks(raw)
    if not chunks:
        log.warning(
            "LightRAG 上下文未解析到 Document Chunks（可能格式变更），原始长度=%s",
            len(raw),
        )
        return "", []

    deduped = dedupe_job_chunks(chunks, ref_map=ref_map)
    if not deduped:
        log.warning(
            "LightRAG Document Chunks 解析成功但无有效岗位条目，chunks=%s",
            len(chunks),
        )
        return "", []

    material = format_deduped_job_retrieval_context(deduped)
    log.info(
        "LightRAG 素材净化：原始=%s 字符 → 岗位=%s 条 / %s 字符",
        len(raw),
        len(deduped),
        len(material),
    )
    return material, deduped
