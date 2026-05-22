"""联网搜索子进程封装。"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.portal.errors import PortalError
from app.portal.paths import AI_JOB_ROOT


def run_online_search(
    query: str, engine: str, topk: int, deep_search: bool
) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        raise PortalError("query 不能为空", 400)

    chosen_engine = (engine or "baidu").strip().lower()
    if chosen_engine not in {"baidu", "duckduckgo"}:
        raise PortalError("engine 仅支持 baidu 或 duckduckgo", 400)

    k = max(1, min(int(topk), 10))
    output_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="online-search-",
            delete=False,
            dir=str(AI_JOB_ROOT),
        ) as tmp:
            output_path = Path(tmp.name)
    except OSError as exc:
        raise PortalError(f"无法创建临时文件: {exc}", 500) from exc

    # 使用 -m：若以脚本路径启动，sys.path[0] 为 online_search/，无法解析包名 online_search.*
    cmd = [
        sys.executable,
        "-m",
        "online_search.search_answer_spider",
        "--query",
        q,
        "--engine",
        chosen_engine,
        "--topk",
        str(k),
        "--deep-search",
        "true" if deep_search else "false",
        "--output",
        str(output_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(AI_JOB_ROOT),
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if proc.returncode != 0:
            msg = (
                "在线搜索执行失败: "
                + (proc.stderr.strip() or proc.stdout.strip() or "未知错误")
            )[:500]
            raise PortalError(msg, 502)

        if not output_path.exists():
            return {"query": q, "engine": chosen_engine, "items": []}

        with output_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        items: List[Any] = data if isinstance(data, list) else []
        return {
            "query": q,
            "engine": chosen_engine,
            "topk": k,
            "deep_search": deep_search,
            "count": len(items),
            "items": items,
        }
    except subprocess.TimeoutExpired as exc:
        raise PortalError("在线搜索超时，请稍后重试", 504) from exc
    finally:
        if output_path is not None:
            try:
                output_path.unlink(missing_ok=True)
            except Exception:
                pass
