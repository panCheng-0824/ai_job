"""智能采集流式输出：NDJSON over chunked HTTP（非 SSE）。"""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Iterator
from typing import Any

from app.portal.errors import PortalError
from app.portal.schemas import AiSearchCrawlRequest

logger = logging.getLogger(__name__)

NDJSON_MEDIA = "application/x-ndjson; charset=utf-8"


class _NdjsonQueueHandler(logging.Handler):
    """将 ai_search 模块日志写入队列，供流式响应读取。"""

    def __init__(self, q: queue.Queue[str]):
        super().__init__()
        self._queue = q
        self.setFormatter(logging.Formatter("%(message)s"))
        self.addFilter(_AiSearchLogFilter())

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if msg:
                self._queue.put(msg)
        except Exception:
            self.handleError(record)


class _AiSearchLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("ai_search")


def validate_crawl_request(payload: AiSearchCrawlRequest) -> None:
    """校验采集请求（流式/同步共用）。"""
    _validate_request(payload)


def _validate_request(payload: AiSearchCrawlRequest) -> None:
    target = (payload.url or "").strip()
    if not target:
        raise PortalError("url 不能为空", 400)
    if not target.startswith(("http://", "https://")):
        raise PortalError("url 需以 http:// 或 https:// 开头", 400)
    mode = (payload.mode or "scrapy").strip().lower()
    if mode not in {"auto", "hybrid", "scrapy", "drission"}:
        raise PortalError("mode 仅支持: auto, hybrid, scrapy, drission", 400)
    if payload.require_login or mode == "hybrid":
        raise PortalError(
            "当前 API 不支持需登录/混合模式（请在 CLI 有头浏览器中完成登录）",
            400,
        )


def _build_task(payload: AiSearchCrawlRequest):
    from ai_search.models import CrawlMode, CrawlTask

    return CrawlTask(
        url=payload.url.strip(),
        prompt=(payload.prompt or "").strip(),
        mode=CrawlMode((payload.mode or "scrapy").strip().lower()),
        require_login=False,
        max_pages=max(1, min(int(payload.max_pages), 20)),
        follow_links=bool(payload.follow_links),
        link_selector=(payload.link_selector or "").strip(),
        output_path="ai_search/output_api.json",
        meta_path="ai_search/meta_api.json",
    )


def _encode_line(event: str, **fields: Any) -> bytes:
    payload = {"event": event, **fields}
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def iter_crawl_stream(payload: AiSearchCrawlRequest) -> Iterator[bytes]:
    """
    流式执行采集：每行一个 JSON 对象（NDJSON）。

    事件类型：
    - log: 运行步骤日志
    - result: 最终结果
    - error: 错误信息
    """
    _validate_request(payload)

    log_queue: queue.Queue[str | None] = queue.Queue()
    result_box: dict[str, Any] = {}
    error_box: dict[str, str] = {}

    handler = _NdjsonQueueHandler(log_queue)

    root = logging.getLogger("ai_search")
    prev_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    def _worker() -> None:
        try:
            from ai_search.orchestrator import run_task

            task = _build_task(payload)
            result = run_task(task)
            result_box["data"] = result.to_dict()
            result_box["meta"] = {
                "mode_used": result.mode_used.value,
                "session_reused": result.session_reused,
                "llm_used": result.llm_used,
                "page_count": len(result.pages),
                "errors": result.errors,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
            }
        except Exception as exc:
            logger.exception("流式采集任务失败")
            error_box["detail"] = str(exc)
        finally:
            log_queue.put(None)

    thread = threading.Thread(target=_worker, name="ai-search-crawl", daemon=True)
    thread.start()

    yield _encode_line("start", url=payload.url.strip(), mode=payload.mode)

    try:
        while True:
            try:
                item = log_queue.get(timeout=0.25)
            except queue.Empty:
                if not thread.is_alive():
                    break
                continue
            if item is None:
                break
            yield _encode_line("log", message=item)

        thread.join(timeout=600)

        if error_box:
            yield _encode_line("error", detail=error_box.get("detail", "unknown"))
        elif result_box:
            yield _encode_line(
                "result",
                data=result_box.get("data"),
                meta=result_box.get("meta"),
            )
        else:
            yield _encode_line("error", detail="采集未返回结果")
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)
