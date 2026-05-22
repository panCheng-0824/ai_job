import argparse

from scrapy.crawler import CrawlerProcess

from online_search.search_answer_config import DEMO_QUERIES


def parse_bool_flag(raw: str) -> bool:
    text = str(raw or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("deep_search 仅支持 true/false/1/0")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据问题抓取搜索结果前5条并提取正文")
    parser.add_argument(
        "--query",
        default="",
        help="搜索问题，例如：如何准备算法面试；不传时会使用内置测试 query",
    )
    parser.add_argument(
        "--demo",
        type=int,
        choices=range(1, len(DEMO_QUERIES) + 1),
        default=1,
        help=f"使用内置测试问题编号，范围 1-{len(DEMO_QUERIES)}，默认 1",
    )
    parser.add_argument(
        "--engine",
        default="baidu",
        choices=["baidu", "duckduckgo"],
        help="搜索引擎，默认 baidu",
    )
    parser.add_argument("--topk", type=int, default=5, help="抓取前 N 条，默认 5")
    parser.add_argument(
        "--deep-search",
        type=parse_bool_flag,
        default=False,
        help="是否深度搜索（访问详情页提取正文），默认 false",
    )
    parser.add_argument("--output", default="output.json", help="输出文件路径，默认 output.json")
    return parser


def run_spider(spider_cls):
    args = build_parser().parse_args()
    query = args.query.strip() or DEMO_QUERIES[args.demo - 1]
    process = CrawlerProcess(
        settings={
            "FEEDS": {
                args.output: {
                    "format": "json",
                    "encoding": "utf8",
                    "indent": 2,
                    "overwrite": True,
                }
            }
        }
    )
    process.crawl(
        spider_cls,
        query=query,
        engine=args.engine,
        topk=args.topk,
        deep_search=args.deep_search,
    )
    process.start()
