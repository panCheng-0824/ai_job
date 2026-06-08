"""会话快照的本地读写与过期检测。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ai_search.step_log import log_phase, log_warn

from .models import SessionSnapshot

logger = logging.getLogger(__name__)

DEFAULT_SESSIONS_DIR = Path(__file__).resolve().parent / "sessions"


def sessions_dir() -> Path:
    path = DEFAULT_SESSIONS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_path(site_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in site_id)
    return sessions_dir() / f"{safe}.json"


def save_session(snapshot: SessionSnapshot) -> Path:
    path = session_path(snapshot.site_id)
    path.write_text(
        json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_phase(
        logger,
        "SESSION",
        "会话已保存",
        site_id=snapshot.site_id,
        path=str(path),
        cookie_count=len(snapshot.cookies),
        expires_at=snapshot.expires_at or "none",
    )
    return path


def load_session(site_id: str) -> SessionSnapshot | None:
    path = session_path(site_id)
    if not path.is_file():
        log_phase(logger, "SESSION", "本地无会话文件", site_id=site_id, path=str(path))
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    snapshot = SessionSnapshot.from_dict(data)
    log_phase(
        logger,
        "SESSION",
        "会话已加载",
        site_id=site_id,
        path=str(path),
        cookie_count=len(snapshot.cookies),
        expires_at=snapshot.expires_at or "none",
    )
    return snapshot


def is_session_expired(snapshot: SessionSnapshot) -> bool:
    if not snapshot.expires_at:
        return False
    try:
        exp = datetime.fromisoformat(snapshot.expires_at.replace("Z", "+00:00"))
        expired = datetime.now(timezone.utc) >= exp
        if expired:
            log_phase(
                logger,
                "SESSION",
                "会话已过期",
                site_id=snapshot.site_id,
                expires_at=snapshot.expires_at,
            )
        return expired
    except ValueError as exc:
        log_warn(logger, "SESSION", "过期时间解析失败", error=str(exc))
        return False


def delete_session(site_id: str) -> None:
    path = session_path(site_id)
    if path.is_file():
        path.unlink()
        log_phase(logger, "SESSION", "会话文件已删除", site_id=site_id, path=str(path))
