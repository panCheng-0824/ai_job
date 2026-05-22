"""
跨同步/异步边界的协程调度。

LightRAG 的 ``priority_limit_async_func_call`` 会把 ``asyncio.PriorityQueue`` 绑定到
创建时所在的事件循环。若在 FastAPI 主循环上初始化单例，又在 ``asyncio.run()``
或子线程新循环里复用，会触发::

    PriorityQueue ... is bound to a different event loop

本模块提供：
- 进程内持久的后台事件循环（供无 running loop 的同步路径使用）；
- ``run_coroutine_sync``：在同步代码中安全执行协程（含「当前线程已有 loop」场景）。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Coroutine, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")

_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_ready = threading.Event()
_bg_lock = threading.Lock()


def get_background_event_loop() -> asyncio.AbstractEventLoop:
    """返回进程内常驻后台事件循环（懒启动、daemon 线程）。"""
    global _bg_loop, _bg_thread
    if _bg_loop is not None and _bg_loop.is_running():
        return _bg_loop
    with _bg_lock:
        if _bg_loop is not None and _bg_loop.is_running():
            return _bg_loop
        _bg_ready.clear()

        def _runner() -> None:
            global _bg_loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _bg_loop = loop
            _bg_ready.set()
            log.debug("后台事件循环已启动, thread=%s", threading.current_thread().name)
            loop.run_forever()

        _bg_thread = threading.Thread(
            target=_runner,
            name="ai_job-async-bridge",
            daemon=True,
        )
        _bg_thread.start()
        if not _bg_ready.wait(timeout=30.0):
            raise RuntimeError("后台事件循环启动超时")
        assert _bg_loop is not None
        return _bg_loop


def run_coroutine_sync(coro: Coroutine[Any, Any, T], *, timeout: float | None = None) -> T:
    """
    在同步上下文中执行协程。

    - 无 running loop：提交到常驻后台循环；
    - 有 running loop：在独立线程里 ``run_coroutine_threadsafe`` 到该 loop，避免嵌套 ``asyncio.run``。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        bg = get_background_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, bg)
        return future.result(timeout=timeout)

    def _wait_on_loop() -> T:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_wait_on_loop).result()
