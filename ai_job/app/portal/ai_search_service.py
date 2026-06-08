"""ai_search 智能采集服务封装。"""

from __future__ import annotations

import logging
from typing import Any

from app.portal.errors import PortalError

logger = logging.getLogger(__name__)

_VALID_MODES = {"auto", "hybrid", "scrapy", "drission"}


def run_ai_search_crawl(
    *,
    url: str,
    prompt: str = "",
    mode: str = "scrapy",
    max_pages: int = 5,
    follow_links: bool = False,
    link_selector: str = "",
    require_login: bool = False,
) -> dict[str, Any]:
    """
    执行 ai_search 采集任务并返回结构化结果。

    Web/API 场景不支持有头浏览器人工登录；require_login 或 hybrid 模式会拒绝。
    """
    target = (url or "").strip()
    if not target:
        raise PortalError("url 不能为空", 400)
    if not target.startswith(("http://", "https://")):
        raise PortalError("url 需以 http:// 或 https:// 开头", 400)

    chosen_mode = (mode or "scrapy").strip().lower()
    if chosen_mode not in _VALID_MODES:
        raise PortalError(
            f"mode 仅支持: {', '.join(sorted(_VALID_MODES))}",
            400,
        )

    if require_login or chosen_mode == "hybrid":
        raise PortalError(
            "当前 API 不支持需登录/混合模式（需在服务器 CLI 有头浏览器中完成登录）。"
            "请使用 scrapy、drission 或 auto 模式。",
            400,
        )

    pages = max(1, min(int(max_pages), 20))

    from ai_search.models import CrawlMode, CrawlTask
    from ai_search.orchestrator import run_task

    logger.info(
        "[API] 智能采集开始: url=%s mode=%s max_pages=%s follow_links=%s",
        target,
        chosen_mode,
        pages,
        follow_links,
    )

    task = CrawlTask(
        url=target,
        prompt=(prompt or "").strip(),
        mode=CrawlMode(chosen_mode),
        require_login=False,
        max_pages=pages,
        follow_links=bool(follow_links),
        link_selector=(link_selector or "").strip(),
        output_path="ai_search/output_api.json",
        meta_path="ai_search/meta_api.json",
    )

    try:
        result = run_task(task)
    except Exception as exc:
        logger.exception("智能采集执行失败")
        raise PortalError(f"智能采集失败: {exc}", 502) from exc

    payload = result.to_dict()
    payload["meta"] = {
        "mode_used": result.mode_used.value,
        "session_reused": result.session_reused,
        "llm_used": result.llm_used,
        "page_count": len(result.pages),
        "errors": result.errors,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }
    logger.info(
        "[API] 智能采集完成: pages=%s mode=%s errors=%s",
        len(result.pages),
        result.mode_used.value,
        len(result.errors),
    )
    return payload
