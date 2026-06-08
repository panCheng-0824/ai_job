"""启动 Scrapy 采集并收集结果。"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from scrapy.crawler import CrawlerProcess

from ai_search.models import PageRecord, SessionSnapshot
from ai_search.scrapy_engine.spider import AiSearchSpider
from ai_search.step_log import log_phase, log_substep

if TYPE_CHECKING:
    from ai_search.models import CrawlTask

logger = logging.getLogger(__name__)


def run_scrapy_crawl(
    task: CrawlTask,
    session: SessionSnapshot | None = None,
    *,
    parent_step: int | None = None,
) -> list[PageRecord]:
    """同步运行 Scrapy，返回页面记录列表。"""
    cookies = session.cookie_dict() if session else {}
    headers = dict(session.headers) if session else {}
    if session and session.user_agent:
        headers.setdefault("User-Agent", session.user_agent)

    log_phase(
        logger,
        "SCRAPY",
        "创建 CrawlerProcess",
        start_url=task.url,
        max_pages=task.max_pages,
        cookie_count=len(cookies),
        link_selector=task.link_selector or "none",
        follow_links=task.follow_links,
    )
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            "scrapy-start",
            "Scrapy 进程即将启动",
            start_url=task.url,
        )

    process = CrawlerProcess(settings={"LOG_LEVEL": "INFO"})
    crawler = process.create_crawler(AiSearchSpider)
    process.crawl(
        crawler,
        start_url=task.url,
        max_pages=task.max_pages,
        follow_links=task.follow_links,
        link_selector=task.link_selector,
        field_selectors_json=json.dumps(task.field_selectors, ensure_ascii=False),
        session_cookies_json=json.dumps(cookies, ensure_ascii=False),
        session_headers_json=json.dumps(headers, ensure_ascii=False),
    )
    process.start()

    spider = crawler.spider
    if spider is None:
        log_phase(logger, "SCRAPY", "Spider 未返回实例，结果为空")
        return []

    records = [
        PageRecord(
            url=item.get("url", ""),
            title=item.get("title", ""),
            body=item.get("body", ""),
            fields=item.get("fields") or {},
        )
        for item in getattr(spider, "items", [])
    ]
    log_phase(
        logger,
        "SCRAPY",
        "采集完成",
        pages=len(records),
        spider_pages=getattr(spider, "page_count", 0),
    )
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            "scrapy-done",
            "Scrapy 阶段结束",
            page_count=len(records),
        )
    return records
