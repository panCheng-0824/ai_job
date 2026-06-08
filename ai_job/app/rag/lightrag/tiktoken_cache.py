"""tiktoken 词表本地缓存与离线加载（OpenAI CDN 不可达时从 jsDelivr 镜像拉取）。"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CACHE_DIR = _PROJECT_ROOT / "data" / "tiktoken_cache"
_DEFAULT_BPE_DIR = _PROJECT_ROOT / "data" / "tiktoken_bpe"

# OpenAI 官方 CDN 在部分网络环境下不可达；@dqbd/tiktoken 的 JSON 可通过 jsDelivr 获取。
_DQBD_JSON_SOURCES: dict[str, tuple[str, ...]] = {
    "o200k_base": (
        "https://cdn.jsdelivr.net/npm/@dqbd/tiktoken@1.0.15/encoders/o200k_base.json",
    ),
    "cl100k_base": (
        "https://cdn.jsdelivr.net/npm/@dqbd/tiktoken@1.0.15/encoders/cl100k_base.json",
    ),
}

_OPENAI_BPE_URLS: dict[str, str] = {
    "o200k_base": "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken",
    "cl100k_base": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
}


def configure_tiktoken_cache() -> Path:
    """设置 TIKTOKEN_CACHE_DIR（可被环境变量覆盖），须在首次使用 tiktoken 前调用。"""
    raw = (os.getenv("TIKTOKEN_CACHE_DIR") or "").strip()
    cache_dir = Path(raw).expanduser().resolve() if raw else _DEFAULT_CACHE_DIR.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache_dir)
    _DEFAULT_BPE_DIR.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _encoding_name_for_model(model_name: str) -> str:
    import tiktoken

    return tiktoken.encoding_name_for_model((model_name or "gpt-4o-mini").strip() or "gpt-4o-mini")


def _local_bpe_json(encoding_name: str) -> Path:
    return _DEFAULT_BPE_DIR / f"{encoding_name}.json"


def _download_bytes(url: str, timeout: float = 120.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ai_job-tiktoken-cache/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def ensure_bpe_json(encoding_name: str) -> Path:
    """确保本地存在 dqbd 词表 JSON；缺失时从 jsDelivr 下载。"""
    path = _local_bpe_json(encoding_name)
    if path.is_file() and path.stat().st_size > 0:
        return path

    sources = _DQBD_JSON_SOURCES.get(encoding_name, ())
    if not sources:
        raise FileNotFoundError(f"无可用离线词表镜像: encoding={encoding_name}")

    last_err: Exception | None = None
    for url in sources:
        try:
            log.info("tiktoken 离线词表下载开始, encoding=%s, url=%s", encoding_name, url)
            raw = _download_bytes(url)
            data = json.loads(raw.decode("utf-8"))
            if "bpe_ranks" not in data or "pat_str" not in data:
                raise ValueError(f"词表 JSON 结构无效: {url}")
            path.write_bytes(raw)
            log.info("tiktoken 离线词表下载完成, encoding=%s, path=%s, bytes=%s", encoding_name, path, len(raw))
            return path
        except Exception as exc:
            last_err = exc
            log.warning("tiktoken 离线词表下载失败, encoding=%s, url=%s, error=%s", encoding_name, url, exc)

    raise RuntimeError(f"无法下载 tiktoken 词表 JSON, encoding={encoding_name}") from last_err


def _parse_dqbd_mergeable_ranks(bpe_ranks: str) -> dict[bytes, int]:
    parts = (bpe_ranks or "").split(" ")
    if len(parts) < 2:
        raise ValueError("dqbd bpe_ranks 为空或格式不正确")

    mergeable: dict[bytes, int] = {}
    import base64

    first_tok = parts[0].encode("utf-8")
    mergeable[first_tok] = int(parts[1])
    for rank, b64 in enumerate(parts[2:], start=2):
        mergeable[base64.b64decode(b64)] = rank
    return mergeable


def build_encoding_from_dqbd_json(data: dict[str, Any], encoding_name: str):
    """从 @dqbd/tiktoken JSON 构建 tiktoken.Encoding。"""
    from tiktoken.core import Encoding

    mergeable_ranks = _parse_dqbd_mergeable_ranks(str(data.get("bpe_ranks", "")))
    special_tokens = {str(k): int(v) for k, v in (data.get("special_tokens") or {}).items()}
    return Encoding(
        name=encoding_name,
        pat_str=str(data["pat_str"]),
        mergeable_ranks=mergeable_ranks,
        special_tokens=special_tokens,
    )


def load_encoding_offline(model_name: str):
    """优先 tiktoken 本地缓存；失败则从 dqbd JSON 构建。"""
    name = (model_name or "gpt-4o-mini").strip() or "gpt-4o-mini"
    configure_tiktoken_cache()
    encoding_name = _encoding_name_for_model(name)

    try:
        import tiktoken

        enc = tiktoken.encoding_for_model(name)
        log.info("tiktoken 词表就绪(标准缓存), model=%s, encoding=%s", name, enc.name)
        return enc, "tiktoken"
    except Exception as primary_err:
        log.warning(
            "tiktoken 标准加载失败，尝试离线 JSON 词表, model=%s, encoding=%s, error=%s",
            name,
            encoding_name,
            primary_err,
        )

    json_path = ensure_bpe_json(encoding_name)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    enc = build_encoding_from_dqbd_json(data, encoding_name)
    log.info(
        "tiktoken 词表就绪(离线 JSON), model=%s, encoding=%s, json=%s",
        name,
        enc.name,
        json_path,
    )
    return enc, "dqbd_json"


def warmup_tiktoken_encoding(model_name: str) -> str:
    """预加载词表；返回 encoding 名称。"""
    enc, _ = load_encoding_offline(model_name)
    return enc.name


def build_lightrag_tokenizer(model_name: str):
    """
    构建 LightRAG Tokenizer：
    1. tiktoken 本地缓存
    2. dqbd JSON 离线词表
    3. 字符级回退
    """
    from lightrag.utils import Tokenizer

    from .fallback_tokenizer import build_char_tokenizer

    name = (model_name or "gpt-4o-mini").strip() or "gpt-4o-mini"

    try:
        enc, source = load_encoding_offline(name)

        class _Backend:
            def encode(self, content: str) -> list[int]:
                return enc.encode(content)

            def decode(self, tokens: list[int]) -> str:
                return enc.decode(tokens)

        tokenizer = Tokenizer(model_name=name, tokenizer=_Backend())
        log.info("LightRAG Tokenizer 就绪, model=%s, encoding=%s, source=%s", name, enc.name, source)
        return tokenizer
    except Exception as exc:
        log.warning(
            "tiktoken 离线词表不可用，回退字符级分词（chunk 粒度偏粗）, model=%s, error=%s",
            name,
            exc,
        )
        return build_char_tokenizer(name)


def seed_openai_cache_from_dqbd(encoding_name: str) -> bool:
    """
    可选：将 dqbd JSON 转成 OpenAI .tiktoken 缓存文件，供原生 tiktoken 直接命中。
    若 hash 不一致则跳过（不影响离线 JSON 路径）。
    """
    openai_url = _OPENAI_BPE_URLS.get(encoding_name)
    if not openai_url:
        return False

    cache_dir = configure_tiktoken_cache()
    cache_key = hashlib.sha1(openai_url.encode()).hexdigest()
    cache_path = cache_dir / cache_key
    if cache_path.is_file():
        return True

    try:
        json_path = ensure_bpe_json(encoding_name)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        parts = str(data["bpe_ranks"]).split(" ")
        import base64

        lines = [f"{base64.b64encode(parts[0].encode()).decode()} {parts[1]}"]
        lines.extend(f"{b64} {rank}" for rank, b64 in enumerate(parts[2:], start=2))
        raw = ("\n".join(lines) + "\n").encode("utf-8")
        cache_path.write_bytes(raw)
        log.info("tiktoken OpenAI 缓存已写入(来自 dqbd JSON), encoding=%s, path=%s", encoding_name, cache_path)
        return True
    except Exception as exc:
        log.debug("tiktoken OpenAI 缓存写入跳过, encoding=%s, error=%s", encoding_name, exc)
        return False
