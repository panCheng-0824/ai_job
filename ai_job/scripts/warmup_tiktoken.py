#!/usr/bin/env python3
"""预下载 LightRAG 所需的 tiktoken 词表到 ai_job/data/tiktoken_bpe（jsDelivr 镜像，仅需执行一次）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from app.rag.lightrag.config import load_lightrag_config_from_env
from app.rag.lightrag.tiktoken_cache import (
    configure_tiktoken_cache,
    ensure_bpe_json,
    load_encoding_offline,
    warmup_tiktoken_encoding,
)


def main() -> None:
    cfg = load_lightrag_config_from_env()
    cache = configure_tiktoken_cache()
    enc, source = load_encoding_offline(cfg.tiktoken_model_name)
    json_path = ensure_bpe_json(enc.name)
    warmup_tiktoken_encoding(cfg.tiktoken_model_name)
    print(
        f"OK: model={cfg.tiktoken_model_name}, encoding={enc.name}, source={source}, "
        f"bpe_json={json_path}, cache_dir={cache}"
    )


if __name__ == "__main__":
    main()
