import scrapy
from twisted.internet.error import TimeoutError as TwistedTimeoutError
from twisted.web._newclient import ResponseNeverReceived

from online_search.search_answer_cli import run_spider
from online_search.search_answer_config import (
    AD_KEYWORDS,
    MAX_AD_KEYWORD_HITS,
    MIN_BODY_LEN,
    REQUEST_TIMEOUT_SECONDS,
    SPIDER_CUSTOM_SETTINGS,
    build_search_request,
    build_search_url,
)
from online_search.search_answer_extractors import extract_body_text
from online_search.search_answer_parsers import (
    parse_baidu_search,
    parse_duckduckgo_search,
)


class SearchAnswerSpider(scrapy.Spider):
    # 爬虫名称，可用于 scrapy crawl 调用
    name = "search_answer"

    # 爬虫运行参数：超时、并发、重试、自动限速和日志等级
    custom_settings = SPIDER_CUSTOM_SETTINGS

    def __init__(self, query="", engine="baidu", topk=5, deep_search=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 搜索关键词、搜索引擎、抓取条数上限
        self.query = query
        self.engine = engine
        self.topk = int(topk)
        self.deep_search = bool(deep_search)
        # 已采集数量 + URL 去重集合
        # collected: 当前已经“成功入队详情页抓取”的数量，不是最终落盘数量
        self.collected = 0
        self.seen_urls = set()
        # 统计详情页产出条数，便于结束时输出摘要日志
        self.item_count = 0
        # 检索与过滤统计
        self.retrieved_count = 0
        self.filtered_count = 0
        self.filtered_search_count = 0
        self.filtered_detail_count = 0
        self.timeout_count = 0
        self.request_error_count = 0
        self.logger.info(
            "[INIT] 参数初始化完成: query=%s, engine=%s, topk=%s, deep_search=%s, settings=%s",
            self.query,
            self.engine,
            self.topk,
            self.deep_search,
            {
                "DOWNLOAD_TIMEOUT": self.custom_settings.get("DOWNLOAD_TIMEOUT"),
                "CONCURRENT_REQUESTS": self.custom_settings.get("CONCURRENT_REQUESTS"),
                "RETRY_TIMES": self.custom_settings.get("RETRY_TIMES"),
                "AUTOTHROTTLE_ENABLED": self.custom_settings.get("AUTOTHROTTLE_ENABLED"),
                "LOG_LEVEL": self.custom_settings.get("LOG_LEVEL"),
                "REQUEST_TIMEOUT_SECONDS": REQUEST_TIMEOUT_SECONDS,
                "CLOSESPIDER_TIMEOUT": self.custom_settings.get("CLOSESPIDER_TIMEOUT"),
            },
        )

    async def start(self):
        # STEP 1: Scrapy 2.13+ 推荐入口
        # 作用：发起“搜索结果页”请求，后续在 parse_search 中拆分详情页任务
        if not self.query:
            raise ValueError("query 不能为空")
        url = build_search_url(engine=self.engine, query=self.query)
        self.logger.info(
            "[STEP 1] 开始入口请求: 引擎=%s, 关键词=%s, 抓取上限=%s, 地址=%s",
            self.engine,
            self.query,
            self.topk,
            url,
        )
        yield build_search_request(url=url, callback=self.parse_search).replace(errback=self.on_request_error)

    def start_requests(self):
        # STEP 1(兼容): 兼容旧版 Scrapy（2.12 及以下）
        if not self.query:
            raise ValueError("query 不能为空")
        url = build_search_url(engine=self.engine, query=self.query)
        self.logger.info(
            "[STEP 1-COMPAT] 兼容入口请求: 引擎=%s, 关键词=%s, 抓取上限=%s, 地址=%s",
            self.engine,
            self.query,
            self.topk,
            url,
        )
        yield build_search_request(url=url, callback=self.parse_search).replace(errback=self.on_request_error)

    def on_request_error(self, failure):
        request = getattr(failure, "request", None)
        req_url = getattr(request, "url", "-")
        req_rank = request.meta.get("rank") if request and request.meta else "-"
        err_name = failure.value.__class__.__name__
        self.request_error_count += 1
        if failure.check(TwistedTimeoutError, ResponseNeverReceived):
            self.timeout_count += 1
            self.filtered_count += 1
            self.filtered_detail_count += 1
            self.logger.info(
                "[STEP TIMEOUT] 请求超时已放弃: 排名=%s, 地址=%s, timeout=%ss, 错误=%s",
                req_rank,
                req_url,
                REQUEST_TIMEOUT_SECONDS,
                err_name,
            )
            return

        self.logger.info(
            "[STEP ERROR] 请求失败已放弃: 排名=%s, 地址=%s, 错误=%s",
            req_rank,
            req_url,
            err_name,
        )

    def parse_search(self, response):
        # STEP 2: 解析搜索结果页
        # 目标：抽取候选标题/链接/摘要，并派发详情页请求（最多 topk 条）
        self.logger.info(
            "[STEP 2] 解析搜索结果页: 状态码=%s, 地址=%s",
            response.status,
            response.url,
        )
        self.logger.info(
            "[STEP 2-META] 当前统计: 检索=%s, 搜索过滤=%s, 详情过滤=%s, 入队=%s, 输出=%s",
            self.retrieved_count,
            self.filtered_search_count,
            self.filtered_detail_count,
            self.collected,
            self.item_count,
        )
        if self.engine == "baidu":
            yield from parse_baidu_search(spider=self, response=response)
            return

        yield from parse_duckduckgo_search(spider=self, response=response)

    def parse_detail(self, response):
        # STEP 3: 解析详情页正文
        # 说明：先用 readability 提正文主干；失败时退化为段落拼接，保证尽量有文本可用。
        rank = response.meta.get("rank")
        title = response.meta.get("title", "")
        url = response.meta.get("url", response.url)
        snippet = response.meta.get("snippet", "")
        self.logger.info(
            "[STEP 3] 解析详情页: 排名=%s, 状态码=%s, 地址=%s, 标题=%s",
            rank,
            response.status,
            response.url,
            (title[:50] + "...") if len(title) > 50 else title,
        )

        body = extract_body_text(response=response, logger=self.logger)
        self.logger.info(
            "[STEP 3.1] 正文提取完成: 原始长度=%s, 摘要预览=%s",
            len(body),
            (body[:80] + "...") if len(body) > 80 else body,
        )
        if len(body) < MIN_BODY_LEN:
            self.filtered_count += 1
            self.filtered_detail_count += 1
            self.logger.info(
                "[STEP 3-SKIP] 正文过短，疑似低质量/广告页: 排名=%s, 长度=%s, 地址=%s",
                rank,
                len(body),
                url,
            )
            return

        lowered = body.lower()
        ad_hits = sum(1 for kw in AD_KEYWORDS if kw.lower() in lowered)
        if ad_hits >= MAX_AD_KEYWORD_HITS:
            self.filtered_count += 1
            self.filtered_detail_count += 1
            self.logger.info(
                "[STEP 3-SKIP] 广告关键词命中过多: 排名=%s, 命中=%s, 地址=%s",
                rank,
                ad_hits,
                url,
            )
            return

        final_rank = self.item_count + 1
        self.item_count = final_rank
        self.logger.info(
            "[STEP 3-END] 输出结果 #%s 原始排名=%s 重排排名=%s 正文长度=%s 当前统计(检索=%s,过滤=%s)",
            self.item_count,
            rank,
            final_rank,
            len(body),
            self.retrieved_count,
            self.filtered_count,
        )

        # STEP 4: 输出结构化结果，供后续存储或摘要
        yield {
            "query": self.query,
            "rank": final_rank,
            "source_rank": rank,
            "title": title,
            "url": url,
            "snippet": snippet,
            "body": body,
        }

    def closed(self, reason):
        # 爬虫生命周期结束时打印总览，便于快速定位“为何 0 item”
        self.logger.info(
            (
                "[STEP FINAL] 爬虫结束: 原因=%s, 检索条数=%s, 过滤条数=%s "
                "(搜索页过滤=%s, 详情页过滤=%s), 超时放弃=%s, 请求失败=%s, "
                "入队详情页=%s, 输出结果=%s, 去重后地址数=%s"
            ),
            reason,
            self.retrieved_count,
            self.filtered_count,
            self.filtered_search_count,
            self.filtered_detail_count,
            self.timeout_count,
            self.request_error_count,
            self.collected,
            self.item_count,
            len(self.seen_urls),
        )


def main():
    run_spider(SearchAnswerSpider)


if __name__ == "__main__":
    # 允许作为脚本直接运行
    main()
