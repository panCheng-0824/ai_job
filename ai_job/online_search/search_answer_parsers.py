from online_search.search_answer_filters import classify_link, normalize_url
from online_search.search_answer_config import REQUEST_TIMEOUT_SECONDS


def enqueue_detail_request(spider, response, title: str, url: str, snippet: str = ""):
    spider.collected += 1
    current_rank = spider.collected
    if not getattr(spider, "deep_search", False):
        spider.item_count += 1
        spider.logger.info(
            "[STEP 2.2-OUTPUT] 浅搜索直接输出 #%s 原始排名=%s 标题=%s 地址=%s",
            spider.item_count,
            current_rank,
            (title[:40] + "...") if len(title) > 40 else title,
            url,
        )
        return {
            "query": spider.query,
            "rank": spider.item_count,
            "source_rank": current_rank,
            "title": title,
            "url": url,
            "snippet": snippet,
            "body": "",
        }

    spider.logger.info(
        "[STEP 2.2] 详情页入队 #%s 标题=%s 地址=%s",
        current_rank,
        (title[:40] + "...") if len(title) > 40 else title,
        url,
    )
    return response.follow(
        url=url,
        callback=spider.parse_detail,
        errback=spider.on_request_error,
        dont_filter=True,
        meta={
            "rank": current_rank,
            "title": title,
            "url": url,
            "snippet": snippet,
            "download_timeout": REQUEST_TIMEOUT_SECONDS,
        },
    )


def parse_baidu_search(spider, response):
    blocks = response.css("div.result, div.result-op, div.c-container, div[data-log]")
    spider.logger.info("[STEP 2.1] 百度候选区块命中数量: %s", len(blocks))

    matched = 0
    candidate_no = 0
    for block in blocks:
        if spider.collected >= spider.topk:
            spider.logger.info("[STEP 2.1-STOP] 已达到抓取上限 topk=%s，停止继续扫描", spider.topk)
            break

        candidate_no += 1
        title = "".join(
            block.css("h3 a ::text, h3::text, a[data-click] ::text").getall()
        ).strip()
        url = block.css("h3 a::attr(href), a[data-click]::attr(href), a::attr(href)").get()
        snippet = "".join(
            block.css("div.c-abstract ::text, span.content-right_8Zs40 ::text").getall()
        ).strip()
        spider.logger.info(
            "[STEP 2.1-CANDIDATE] 百度候选 #%s 标题=%s 原始地址=%s",
            candidate_no,
            (title[:40] + "...") if len(title) > 40 else title,
            url or "-",
        )

        if not url or not url.startswith("http"):
            spider.logger.info("[STEP 2.1-SKIP] 候选 #%s 非法地址，跳过", candidate_no)
            continue
        url = normalize_url(url)
        if url in spider.seen_urls:
            spider.logger.info("[STEP 2.1-SKIP] 候选 #%s 地址重复，跳过: %s", candidate_no, url)
            continue
        spider.retrieved_count += 1
        blocked, reason = classify_link(title=title, url=url, snippet=snippet)
        if blocked:
            spider.filtered_count += 1
            spider.filtered_search_count += 1
            spider.logger.info(
                "[STEP 2.2-SKIP] 候选 #%s 命中过滤规则(%s): %s",
                candidate_no,
                reason,
                url,
            )
            continue

        spider.seen_urls.add(url)
        matched += 1
        yield enqueue_detail_request(spider, response, title=title, url=url, snippet=snippet)

    if matched == 0 and spider.collected < spider.topk:
        spider.logger.info("[STEP 2.4] 百度区块解析命中为 0，启用兜底解析器")
        for a in response.css("h3 a"):
            if spider.collected >= spider.topk:
                spider.logger.info("[STEP 2.4-STOP] 兜底解析达到 topk=%s，停止", spider.topk)
                break

            title = "".join(a.css("::text").getall()).strip()
            url = a.css("::attr(href)").get()
            if not url or not url.startswith("http"):
                spider.logger.info("[STEP 2.4-SKIP] 兜底候选非法地址，跳过")
                continue
            url = normalize_url(url)
            if url in spider.seen_urls:
                spider.logger.info("[STEP 2.4-SKIP] 兜底候选地址重复，跳过: %s", url)
                continue
            spider.retrieved_count += 1
            blocked, reason = classify_link(title=title, url=url, snippet="")
            if blocked:
                spider.filtered_count += 1
                spider.filtered_search_count += 1
                spider.logger.info("[STEP 2.5-SKIP] 兜底候选命中过滤规则(%s): %s", reason, url)
                continue

            spider.seen_urls.add(url)
            spider.logger.info(
                "[STEP 2.5] 兜底详情页入队 #%s 标题=%s 地址=%s",
                spider.collected + 1,
                (title[:40] + "...") if len(title) > 40 else title,
                url,
            )
            yield enqueue_detail_request(spider, response, title=title, url=url, snippet="")

    spider.logger.info(
        "[STEP 2-END] 百度结果入队完成: 详情页数量=%s, 去重后地址数=%s",
        spider.collected,
        len(spider.seen_urls),
    )


def parse_duckduckgo_search(spider, response):
    spider.logger.info("[STEP 2.1] 使用 DuckDuckGo 解析器")
    candidate_no = 0
    for a in response.css("a.result__a"):
        if spider.collected >= spider.topk:
            spider.logger.info("[STEP 2.1-STOP] 已达到抓取上限 topk=%s，停止继续扫描", spider.topk)
            break

        candidate_no += 1
        title = "".join(a.css("::text").getall()).strip()
        url = a.css("::attr(href)").get()
        spider.logger.info(
            "[STEP 2.1-CANDIDATE] DuckDuckGo候选 #%s 标题=%s 原始地址=%s",
            candidate_no,
            (title[:40] + "...") if len(title) > 40 else title,
            url or "-",
        )
        if not url or not url.startswith("http"):
            spider.logger.info("[STEP 2.1-SKIP] 候选 #%s 非法地址，跳过", candidate_no)
            continue
        url = normalize_url(url)
        if url in spider.seen_urls:
            spider.logger.info("[STEP 2.1-SKIP] 候选 #%s 地址重复，跳过: %s", candidate_no, url)
            continue
        spider.retrieved_count += 1
        blocked, reason = classify_link(title=title, url=url, snippet="")
        if blocked:
            spider.filtered_count += 1
            spider.filtered_search_count += 1
            spider.logger.info(
                "[STEP 2.2-SKIP] 候选 #%s 命中过滤规则(%s): %s",
                candidate_no,
                reason,
                url,
            )
            continue

        spider.seen_urls.add(url)
        yield enqueue_detail_request(spider, response, title=title, url=url, snippet="")

    spider.logger.info(
        "[STEP 2-END] DuckDuckGo 入队完成: 详情页数量=%s, 去重后地址数=%s",
        spider.collected,
        len(spider.seen_urls),
    )
