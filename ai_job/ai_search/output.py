"""结果与元信息落盘。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ai_search.step_log import log_phase

from .models import CrawlResult, SessionSnapshot

logger = logging.getLogger(__name__)


def write_json(path: str | Path, data: dict) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    p.write_text(text, encoding="utf-8")
    log_phase(logger, "OUTPUT", "JSON 已写入", path=str(p.resolve()), size=len(text))
    return p


def write_result(result: CrawlResult) -> tuple[Path, Path]:
    out = write_json(result.task.output_path, result.to_dict())
    meta = {
        "mode_used": result.mode_used.value,
        "session_reused": result.session_reused,
        "llm_used": result.llm_used,
        "page_count": len(result.pages),
        "errors": result.errors,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }
    meta_path = write_json(result.task.meta_path, meta)
    log_phase(
        logger,
        "OUTPUT",
        "任务结果落盘完成",
        output=str(out),
        meta=str(meta_path),
        pages=len(result.pages),
    )
    return out, meta_path


def write_session_meta(snapshot: SessionSnapshot, path: str | Path) -> Path:
    return write_json(path, snapshot.to_dict())
