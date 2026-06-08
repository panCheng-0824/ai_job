"""AI 驱动智能网页采集：编排入口在 ai_search，ocr / online_search 仅作底层能力。"""

from .models import CrawlMode, CrawlResult, CrawlTask, SessionSnapshot


def run_task(task: CrawlTask) -> CrawlResult:
    from .orchestrator import run_task as _run

    return _run(task)


__all__ = [
    "CrawlMode",
    "CrawlTask",
    "CrawlResult",
    "SessionSnapshot",
    "run_task",
]
