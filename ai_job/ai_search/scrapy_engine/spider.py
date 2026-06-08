"""通用会话注入型采集 Spider。"""

from __future__ import annotations

import json
import logging
from urllib.parse import urljoin, urlparse

import scrapy

from ai_search.scrapy_engine.extractors import (
    extract_body_text,
    extract_fields_with_selectors,
)
from ai_search.scrapy_engine.settings import SPIDER_CUSTOM_SETTINGS

logger = logging.getLogger(__name__)


class AiSearchSpider(scrapy.Spider):
    name = "ai_search_crawl"

    custom_settings = SPIDER_CUSTOM_SETTINGS

    def __init__(
        self,
        start_url: str = "",
        max_pages: int = 10,
        follow_links: bool = False,
        link_selector: str = "",
        field_selectors_json: str = "{}",
        session_cookies_json: str = "{}",
        session_headers_json: str = "{}",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.start_url = start_url
        self.max_pages = int(max_pages)
        self.follow_links = str(follow_links).lower() in {"1", "true", "yes"}
        self.link_selector = link_selector or ""
        try:
            self.field_selectors = json.loads(field_selectors_json or "{}")
        except json.JSONDecodeError:
            self.field_selectors = {}
        try:
            self.session_cookies = json.loads(session_cookies_json or "{}")
        except json.JSONDecodeError:
            self.session_cookies = {}
        try:
            self.session_headers = json.loads(session_headers_json or "{}")
        except json.JSONDecodeError:
            self.session_headers = {}
        self.seen_urls: set[str] = set()
        self.page_count = 0
        self.items: list[dict] = []
        self.logger.info(
            "[INIT] Spider 参数初始化: start_url=%s, max_pages=%s, follow_links=%s, "
            "link_selector=%s, cookie_count=%s, field_selectors=%s",
            self.start_url,
            self.max_pages,
            self.follow_links,
            self.link_selector or "none",
            len(self.session_cookies),
            list(self.field_selectors.keys()) if self.field_selectors else "none",
        )

    def _request(self, url: str, callback):
        headers = dict(self.session_headers)
        return scrapy.Request(
            url=url,
            callback=callback,
            dont_filter=True,
            cookies=self.session_cookies,
            headers=headers,
            meta={"download_timeout": 20},
        )

    async def start(self):
        if not self.start_url:
            raise ValueError("start_url 不能为空")
        self.logger.info(
            "[STEP 1] Scrapy 入口请求: url=%s, max_pages=%s, follow_links=%s, "
            "link_selector=%s",
            self.start_url,
            self.max_pages,
            self.follow_links,
            self.link_selector or "none",
        )
        yield self._request(self.start_url, self.parse_page)

    def start_requests(self):
        if not self.start_url:
            return
        self.logger.info(
            "[STEP 1-COMPAT] 兼容入口请求: url=%s",
            self.start_url,
        )
        yield self._request(self.start_url, self.parse_page)

    def parse_page(self, response):
        url = response.url
        if url in self.seen_urls:
            self.logger.info("[STEP SKIP] 重复 URL 已跳过: url=%s", url)
            return
        self.seen_urls.add(url)
        self.page_count += 1

        status = getattr(response, "status", "-")
        self.logger.info(
            "[STEP 2] 收到页面响应: rank=%s, status=%s, url=%s",
            self.page_count,
            status,
            url,
        )

        title = (response.css("title::text").get() or "").strip()
        body = extract_body_text(response, self.logger)
        fields = extract_fields_with_selectors(
            response.text,
            self.field_selectors,
        )
        item = {
            "url": url,
            "title": title,
            "body": body,
            "fields": fields,
        }
        self.items.append(item)
        self.logger.info(
            "[STEP 3] 页面解析完成: rank=%s, title=%s, body_len=%s, field_keys=%s",
            self.page_count,
            (title[:60] + "…") if len(title) > 60 else (title or "none"),
            len(body),
            list(fields.keys()) if fields else "none",
        )
        yield item

        if self.page_count >= self.max_pages:
            self.logger.info(
                "[STEP 4] 已达 max_pages 上限，停止翻页: max_pages=%s",
                self.max_pages,
            )
            return

        next_urls: list[str] = []
        if self.link_selector:
            for href in response.css(f"{self.link_selector}::attr(href)").getall():
                full = urljoin(url, href)
                if self._same_site(self.start_url, full):
                    next_urls.append(full)
            self.logger.info(
                "[STEP 4] link_selector 发现候选链接: selector=%s, count=%s",
                self.link_selector,
                len(next_urls),
            )
        elif self.follow_links:
            for href in response.css("a::attr(href)").getall()[:30]:
                full = urljoin(url, href)
                if self._same_site(self.start_url, full) and full not in self.seen_urls:
                    next_urls.append(full)
            self.logger.info(
                "[STEP 4] follow_links 发现候选链接: count=%s",
                len(next_urls),
            )

        queued = 0
        for next_url in next_urls:
            if self.page_count + queued >= self.max_pages:
                break
            if next_url in self.seen_urls:
                continue
            queued += 1
            self.logger.info(
                "[STEP 5] 派发下一页请求: rank=%s, url=%s",
                self.page_count + queued,
                next_url,
            )
            yield self._request(next_url, self.parse_page)

    @staticmethod
    def _same_site(base_url: str, other: str) -> bool:
        b = urlparse(base_url).netloc
        o = urlparse(other).netloc
        return bool(b and o and b == o)

    def closed(self, reason):
        self.logger.info(
            "[DONE] Spider 结束: reason=%s, pages=%s, items=%s",
            reason,
            self.page_count,
            len(self.items),
        )
