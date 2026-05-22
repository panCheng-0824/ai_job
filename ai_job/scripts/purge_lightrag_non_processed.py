#!/usr/bin/env python3
"""删除 LightRAG 中 status 非 processed 的文档（pending / processing / failed）。

默认仅 dry-run，打印待删 doc_id；加 --execute 才真正调用 adelete_by_doc_id。

用法（在 ai_job 项目根目录执行；需与 LightRAG 一致 **Python>=3.10** 及已配置 .env）::

    cd /path/to/ai_job
    source .venv/bin/activate   # 或你实际使用的 3.10+ 虚拟环境
    python scripts/purge_lightrag_non_processed.py
    python scripts/purge_lightrag_non_processed.py --execute
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)


def _import_lightrag_service_only():
    """避免执行 app.rag / app.rag.lightrag 的 __init__（会拉 FastAPI 路由与 Pydantic v2 模型）。"""
    rag_pkg = types.ModuleType("app.rag")
    rag_pkg.__path__ = [str(ROOT / "app" / "rag")]
    sys.modules.setdefault("app.rag", rag_pkg)
    lr_pkg = types.ModuleType("app.rag.lightrag")
    lr_pkg.__path__ = [str(ROOT / "app" / "rag" / "lightrag")]
    sys.modules.setdefault("app.rag.lightrag", lr_pkg)
    mod = importlib.import_module("app.rag.lightrag.service")
    return mod.get_lightrag_service


async def _run(*, execute: bool, max_concurrent: int, no_disk_merge: bool, no_disk_strip: bool) -> None:
    get_lightrag_service = _import_lightrag_service_only()
    svc = get_lightrag_service()
    result = await svc.delete_non_processed_documents(
        dry_run=not execute,
        merge_disk_doc_status=not no_disk_merge,
        max_concurrent_deletes=max_concurrent,
        strip_non_processed_from_disk_doc_status=not no_disk_strip,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="清理 LightRAG 未成功处理的文档")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行删除；省略则仅 dry-run（不删数据）",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=4,
        help="并发删除上限，默认 4",
    )
    parser.add_argument(
        "--no-disk-merge",
        action="store_true",
        help="不合并扫描磁盘上的 kv_store_*doc_status*.json",
    )
    parser.add_argument(
        "--no-disk-strip",
        action="store_true",
        help="不在删除后重写磁盘 doc_status JSON（默认会兜底去掉非 processed 行）",
    )
    args = parser.parse_args()
    asyncio.run(
        _run(
            execute=bool(args.execute),
            max_concurrent=max(1, int(args.max_concurrent)),
            no_disk_merge=bool(args.no_disk_merge),
            no_disk_strip=bool(args.no_disk_strip),
        )
    )


if __name__ == "__main__":
    main()
