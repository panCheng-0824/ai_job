from urllib.parse import quote

import scrapy

DEMO_QUERIES = [
    "如何准备算法面试",
    "人工智能就业趋势",
    "大学生找实习简历怎么写",
]

SPIDER_CUSTOM_SETTINGS = {
    "DOWNLOAD_TIMEOUT": 15,
    "CONCURRENT_REQUESTS": 8,
    "RETRY_TIMES": 2,
    "AUTOTHROTTLE_ENABLED": True,
    "LOG_LEVEL": "INFO",
    "CLOSESPIDER_TIMEOUT": 30,
}

REQUEST_TIMEOUT_SECONDS = 5
CRAWL_TIMEOUT_SECONDS = 15

AD_DOMAIN_BLOCKLIST = {
    "cpro.baidu.com",
    "pos.baidu.com",
    "union.baidu.com",
    "top.baidu.com",
    "ssp.qq.com",
    "guanggao.baidu.com",
}

AD_KEYWORDS = {
    "广告",
    "推广",
    "赞助",
    "开户链接",
    "立即下载",
    "免费领取",
    "送彩金",
    "注册送彩金",
    "点击直达",
}

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "msclkid",
}

MIN_BODY_LEN = 120
MAX_AD_KEYWORD_HITS = 3

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def build_search_url(engine: str, query: str) -> str:
    """根据搜索引擎和 query 生成搜索入口 URL。"""
    if engine == "baidu":
        return f"https://www.baidu.com/s?wd={quote(query)}"
    return f"https://duckduckgo.com/html/?q={quote(query)}"


def build_search_request(url: str, callback):
    """统一构造入口请求。"""
    return scrapy.Request(
        url=url,
        callback=callback,
        dont_filter=True,
        headers=DEFAULT_REQUEST_HEADERS,
        meta={"download_timeout": REQUEST_TIMEOUT_SECONDS},
    )
