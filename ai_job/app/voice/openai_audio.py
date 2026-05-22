"""调用 OpenAI 兼容服务的 /audio/transcriptions 与 /audio/speech。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Tuple

import requests

from model_cfg import ModelEntry, load_model_list

logger = logging.getLogger(__name__)


def pick_model_entry(model_type: str, level: str) -> ModelEntry:
    """按类型与档位选取模型；档位缺失时退化为同类型的第一条。"""
    models = load_model_list()
    want_level = (level or "mid").strip().lower()
    for m in models:
        if m.get("model_type") == model_type and str(m.get("model_level", "")).lower() == want_level:
            return m
    for m in models:
        if m.get("model_type") == model_type:
            return m
    raise ValueError(f"未在 modelCfg.json 中配置 model_type={model_type}")


def _auth_headers(api_key: str) -> Dict[str, str]:
    if not (api_key or "").strip():
        return {}
    return {"Authorization": f"Bearer {api_key.strip()}"}


def _assemble_segment_transcript(items: list[Any]) -> str:
    """将 [{'Start','End','Speaker','Content'}, ...] 按时间顺序拼成一段可读文本。"""
    scored: list[tuple[float, int, str]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        raw = item.get("Content") if "Content" in item else item.get("content")
        if not isinstance(raw, str):
            continue
        piece = raw.strip()
        if not piece:
            continue
        start = item.get("Start", item.get("start"))
        try:
            order = float(start) if start is not None else float(i)
        except (TypeError, ValueError):
            order = float(i)
        scored.append((order, i, piece))
    scored.sort(key=lambda x: (x[0], x[1]))
    return "".join(p for _, _, p in scored)


def _extract_transcript_from_payload(payload: Dict[str, Any]) -> str | None:
    """
    兼容：
    - OpenAI 风格：{"text": "整段文字"}
    - 分段 JSON 字符串：{"text": '[{"Start":0,"Content":"..."}]'}
    - 分段数组：{"text": [ {...}, ... ]}
    - 顶层 segments / Segments 数组
    """
    text_field = payload.get("text")
    if isinstance(text_field, list):
        assembled = _assemble_segment_transcript(text_field)
        return assembled.strip() if assembled else None

    if isinstance(text_field, str):
        s = text_field.strip()
        if not s:
            return None
        if s.startswith("["):
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                return s
            if isinstance(parsed, list):
                assembled = _assemble_segment_transcript(parsed)
                return assembled.strip() if assembled else None
            return s
        return s

    for key in ("segments", "Segments", "chunks", "Chunks"):
        seg = payload.get(key)
        if isinstance(seg, list):
            assembled = _assemble_segment_transcript(seg)
            if assembled.strip():
                return assembled.strip()

    return None


def transcribe_bytes(
    audio: bytes,
    filename: str,
    content_type: str | None,
    model_level: str,
    timeout_sec: int = 120,
) -> str:
    """上传音频到 ASR，返回识别文本。"""
    entry = pick_model_entry("asr", model_level)
    base = entry["model_api"].rstrip("/")
    url = f"{base}/audio/transcriptions"
    mime = content_type or "application/octet-stream"
    files = {"file": (filename or "audio.webm", audio, mime)}
    data: Dict[str, Any] = {"model": entry["model_name"]}
    headers = _auth_headers(entry["model_key"])
    logger.info("ASR 请求: url=%s model=%s bytes=%s", url, entry["model_name"], len(audio))
    resp = requests.post(url, files=files, data=data, headers=headers, timeout=timeout_sec)
    if not resp.ok:
        detail = resp.text[:2000] if resp.text else resp.reason
        logger.warning("ASR 失败: status=%s body=%s", resp.status_code, detail)
        raise RuntimeError(f"ASR 服务返回 {resp.status_code}: {detail}")
    payload = resp.json()
    text = _extract_transcript_from_payload(payload)
    if text:
        return text
    raise RuntimeError(f"ASR 响应无法解析出文本: {payload}")


def synthesize_speech(
    text: str,
    model_level: str,
    voice: str = "serena",
    timeout_sec: int = 120,
) -> Tuple[bytes, str]:
    """TTS：返回音频二进制与 Content-Type。"""
    entry = pick_model_entry("tts", model_level)
    base = entry["model_api"].rstrip("/")
    url = f"{base}/audio/speech"
    body = {
        "model": entry["model_name"],
        "input": text,
        "voice": voice or "serena",
    }
    headers = {**_auth_headers(entry["model_key"]), "Content-Type": "application/json"}
    logger.info("TTS 请求: url=%s model=%s chars=%s", url, entry["model_name"], len(text))
    resp = requests.post(url, json=body, headers=headers, timeout=timeout_sec)
    if not resp.ok:
        detail = resp.text[:2000] if resp.text else resp.reason
        logger.warning("TTS 失败: status=%s body=%s", resp.status_code, detail)
        raise RuntimeError(f"TTS 服务返回 {resp.status_code}: {detail}")
    ctype = resp.headers.get("Content-Type", "audio/mpeg")
    return resp.content, ctype


@dataclass(frozen=True)
class TtsByteStream:
    """上游流式 TTS 响应：content-type + 音频字节迭代器（单次消费）。"""

    content_type: str
    chunks: Iterator[bytes]


def open_tts_stream(
    text: str,
    model_level: str,
    voice: str = "serena",
    timeout_sec: int = 600,
) -> TtsByteStream:
    """请求 OpenAI 兼容 ``/audio/speech``，使用 ``stream=True`` 边生成边读块（适配 OMLX 等）。"""
    entry = pick_model_entry("tts", model_level)
    base = entry["model_api"].rstrip("/")
    url = f"{base}/audio/speech"
    body = {
        "model": entry["model_name"],
        "input": text,
        "voice": voice or "serena",
    }
    headers = {**_auth_headers(entry["model_key"]), "Content-Type": "application/json"}
    logger.info("TTS 流式请求: url=%s model=%s chars=%s", url, entry["model_name"], len(text))
    resp = requests.post(url, json=body, headers=headers, timeout=timeout_sec, stream=True)
    if not resp.ok:
        detail = resp.text[:2000] if resp.text else resp.reason
        resp.close()
        logger.warning("TTS 流式失败: status=%s body=%s", resp.status_code, detail)
        raise RuntimeError(f"TTS 服务返回 {resp.status_code}: {detail}")
    ctype = resp.headers.get("Content-Type", "audio/mpeg")

    def gen() -> Iterator[bytes]:
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        finally:
            resp.close()

    return TtsByteStream(content_type=ctype, chunks=gen())
