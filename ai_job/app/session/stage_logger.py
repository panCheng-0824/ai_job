"""多阶段用户会话管道的简易阶段日志器。"""

from __future__ import annotations

import sys
import time
from typing import Optional


def stage_log(
    enabled: bool,
    trace_id: str,
    stage: str,
    action: str,
    started_at: Optional[float] = None,
) -> None:
    """打印阶段开始/结束标记，并可附带耗时。"""
    if not enabled:
        return
    if action == "start":
        print(f"[run_user_query][trace={trace_id}] {stage} started", file=sys.stderr, flush=True)
        return
    if started_at is None:
        print(f"[run_user_query][trace={trace_id}] {stage} finished", file=sys.stderr, flush=True)
        return
    elapsed = time.monotonic() - started_at
    print(
        f"[run_user_query][trace={trace_id}] {stage} finished in {elapsed:.2f}s",
        file=sys.stderr,
        flush=True,
    )
