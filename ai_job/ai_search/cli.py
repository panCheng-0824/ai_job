"""ai_search 命令行入口。"""

from __future__ import annotations

import argparse
import logging
import sys

from ai_search.models import CrawlMode, CrawlTask
from ai_search.orchestrator import run_task
from ai_search.step_log import log_init

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _parse_mode(raw: str) -> CrawlMode:
    try:
        return CrawlMode(raw.strip().lower())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"无效 mode: {raw}，可选: auto, hybrid, scrapy, drission"
        ) from exc


def _parse_bool(raw: str) -> bool:
    text = str(raw or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("布尔参数仅支持 true/false/1/0")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI 智能网页采集（核心编排：ai_search）",
    )
    parser.add_argument("--url", required=True, help="目标 URL")
    parser.add_argument(
        "--prompt",
        default="",
        help="自然语言采集需求，例如：提取商品名称、价格",
    )
    parser.add_argument(
        "--mode",
        type=_parse_mode,
        default=CrawlMode.HYBRID,
        help="采集模式: auto | hybrid | scrapy | drission",
    )
    parser.add_argument(
        "--require-login",
        type=_parse_bool,
        default=False,
        help="是否需要用户在有头浏览器中登录",
    )
    parser.add_argument("--site-id", default="", help="会话存储标识，默认取域名")
    parser.add_argument("--max-pages", type=int, default=10, help="最大抓取页数")
    parser.add_argument(
        "--follow-links",
        type=_parse_bool,
        default=False,
        help="是否跟随同站链接（未指定 link-selector 时）",
    )
    parser.add_argument(
        "--link-selector",
        default="",
        help="列表/详情链接 CSS 选择器，例如: .item a.title",
    )
    parser.add_argument(
        "--reuse-session",
        type=_parse_bool,
        default=True,
        help="是否复用已保存会话",
    )
    parser.add_argument(
        "--force-relogin",
        type=_parse_bool,
        default=False,
        help="强制重新打开浏览器登录",
    )
    parser.add_argument(
        "--login-wait-seconds",
        type=int,
        default=0,
        help="登录等待秒数（>0 时超时自动继续；0 则按 Enter）",
    )
    parser.add_argument(
        "--output",
        default="ai_search/output.json",
        help="结果 JSON 路径",
    )
    parser.add_argument(
        "--meta",
        default="ai_search/meta.json",
        help="元信息 JSON 路径",
    )
    parser.add_argument(
        "--model-level",
        default="",
        help="LLM 档位（low/mid/high），默认读 AI_SEARCH_MODEL_LEVEL 或 mid",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task = CrawlTask(
        url=args.url.strip(),
        prompt=args.prompt.strip(),
        mode=args.mode,
        require_login=args.require_login,
        site_id=args.site_id.strip(),
        max_pages=args.max_pages,
        follow_links=args.follow_links,
        link_selector=args.link_selector.strip(),
        reuse_session=args.reuse_session,
        force_relogin=args.force_relogin,
        login_wait_seconds=args.login_wait_seconds,
        output_path=args.output,
        meta_path=args.meta,
        model_level=args.model_level.strip(),
    )
    log_init(
        logger,
        "CLI 参数解析完成",
        url=task.url,
        mode=task.mode.value,
        output=task.output_path,
    )
    result = run_task(task)
    print(f"完成: mode={result.mode_used.value} pages={len(result.pages)}")
    if result.errors:
        print("错误:", "; ".join(result.errors), file=sys.stderr)
        return 1
    print(f"结果: {task.output_path}")
    print(f"元信息: {task.meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
