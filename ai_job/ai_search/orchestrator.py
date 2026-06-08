"""采集任务编排：模式选择、登录、Scrapy/浏览器、LLM enrichment。"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone

from ai_search.browser.drission_engine import (
    capture_page_html,
    interactive_login,
)
from ai_search.html_utils import extract_main_text, guess_title
from ai_search.llm.mode_advisor import advise_mode
from ai_search.llm.parse_agent import enrich_pages_with_llm
from ai_search.llm.selector_agent import suggest_link_selector
from ai_search.models import CrawlMode, CrawlResult, CrawlTask, PageRecord, SessionSnapshot
from ai_search.output import write_result
from ai_search.scrapy_engine.runner import run_scrapy_crawl
from ai_search.session_store import (
    delete_session,
    is_session_expired,
    load_session,
    save_session,
)
from ai_search.step_log import log_done, log_error, log_init, log_step, log_substep, log_warn, reset_steps

logger = logging.getLogger(__name__)


def _resolve_session(task: CrawlTask, mode: CrawlMode, step: int) -> tuple[SessionSnapshot | None, bool]:
    """解析会话：可复用则复用；需要时走有头登录。"""
    site_id = task.resolved_site_id()
    log_substep(
        logger,
        step,
        1,
        "开始解析会话",
        site_id=site_id,
        reuse_session=task.reuse_session,
        force_relogin=task.force_relogin,
        require_login=task.require_login,
    )

    if task.reuse_session and not task.force_relogin:
        existing = load_session(site_id)
        if existing and not is_session_expired(existing):
            log_substep(
                logger,
                step,
                2,
                "命中本地会话，直接复用",
                site_id=site_id,
                cookie_count=len(existing.cookies),
                expires_at=existing.expires_at or "none",
            )
            return existing, True
        if existing and is_session_expired(existing):
            log_substep(logger, step, 2, "本地会话已过期，准备删除", site_id=site_id)
            delete_session(site_id)

    must_interactive = task.require_login or task.force_relogin
    if task.force_relogin or must_interactive:
        log_substep(
            logger,
            step,
            3,
            "进入有头浏览器人工登录",
            url=task.url,
            login_wait_seconds=task.login_wait_seconds,
        )
        snapshot = interactive_login(
            task.url,
            site_id=site_id,
            login_wait_seconds=task.login_wait_seconds,
            parent_step=step,
        )
        save_path = save_session(snapshot)
        log_substep(
            logger,
            step,
            4,
            "登录会话已导出并保存",
            site_id=site_id,
            cookie_count=len(snapshot.cookies),
            session_file=str(save_path),
        )
        return snapshot, False

    log_substep(logger, step, 5, "无需交互登录，跳过会话", site_id=site_id)
    return None, False


def _maybe_suggest_link_selector(
    task: CrawlTask,
    session: SessionSnapshot | None,
    step: int,
) -> CrawlTask:
    if task.link_selector or not task.prompt or not task.follow_links:
        log_substep(
            logger,
            step,
            1,
            "跳过链接选择器建议",
            reason="已有 selector 或未开启 follow_links/无 prompt",
            link_selector=task.link_selector or "none",
        )
        return task

    log_substep(
        logger,
        step,
        1,
        "尝试 LLM 建议列表链接选择器",
        url=task.url,
        prompt_preview=task.prompt[:80],
    )
    try:
        html = capture_page_html(task.url, session=session, parent_step=step, sub_step=2)
        selector = suggest_link_selector(
            html,
            task.prompt,
            model_level=task.model_level,
            parent_step=step,
            sub_step=3,
        )
        if selector:
            log_substep(logger, step, 4, "链接选择器建议成功", selector=selector)
            return replace(task, link_selector=selector)
        log_substep(logger, step, 4, "未获得有效链接选择器，使用默认跟随策略")
    except Exception as exc:
        log_warn(logger, "SELECTOR", "链接选择器建议失败", error=str(exc))
    return task


def _run_scrapy_phase(
    task: CrawlTask,
    session: SessionSnapshot | None,
    step: int,
) -> list[PageRecord]:
    log_substep(
        logger,
        step,
        1,
        "启动 Scrapy 收割阶段",
        url=task.url,
        max_pages=task.max_pages,
        follow_links=task.follow_links,
        has_session=bool(session),
    )
    working = _maybe_suggest_link_selector(task, session, step)
    if working.link_selector != task.link_selector:
        log_substep(
            logger,
            step,
            2,
            "应用 LLM 建议的 link_selector",
            selector=working.link_selector,
        )
    return run_scrapy_crawl(working, session, parent_step=step)


def _run_drission_phase(
    task: CrawlTask,
    session: SessionSnapshot | None,
    step: int,
) -> list[PageRecord]:
    log_substep(
        logger,
        step,
        1,
        "启动 DrissionPage 单页采集",
        url=task.url,
        has_session=bool(session),
    )
    html = capture_page_html(task.url, session=session, parent_step=step, sub_step=2)
    log_substep(logger, step, 3, "页面 HTML 已获取", html_len=len(html))
    body = extract_main_text(html)
    title = guess_title(html)
    log_substep(
        logger,
        step,
        4,
        "正文与标题提取完成",
        title=title[:80] if title else "",
        body_len=len(body),
    )
    return [PageRecord(url=task.url, title=title, body=body, fields={})]


def run_task(task: CrawlTask) -> CrawlResult:
    """执行完整采集任务。"""
    reset_steps()
    result = CrawlResult(task=task, mode_used=task.mode)
    session: SessionSnapshot | None = None
    session_reused = False

    log_init(
        logger,
        "采集任务启动",
        url=task.url,
        mode=task.mode.value,
        require_login=task.require_login,
        max_pages=task.max_pages,
        site_id=task.resolved_site_id(),
        prompt_preview=(task.prompt[:60] + "…") if len(task.prompt) > 60 else (task.prompt or "none"),
    )

    try:
        has_session = bool(
            task.reuse_session
            and not task.force_relogin
            and load_session(task.resolved_site_id())
        )
        log_step(
            logger,
            "检查本地会话状态",
            has_cached_session=has_session,
            reuse_session=task.reuse_session,
        )

        mode = task.mode
        if mode == CrawlMode.AUTO:
            auto_step = log_step(logger, "auto 模式：开始决策采集模式", has_session=has_session)
            mode = advise_mode(task, has_session=has_session, parent_step=auto_step)
            log_substep(logger, auto_step, 1, "模式决策完成", mode=mode.value)
        result.mode_used = mode

        session_step = log_step(
            logger,
            "会话准备",
            mode=mode.value,
            require_login=task.require_login,
        )

        if task.require_login or mode == CrawlMode.HYBRID:
            session, session_reused = _resolve_session(task, mode, session_step)
        elif has_session:
            session = load_session(task.resolved_site_id())
            session_reused = True
            log_substep(
                logger,
                session_step,
                1,
                "加载已缓存会话",
                cookie_count=len(session.cookies) if session else 0,
            )
        result.session_reused = session_reused

        crawl_step = log_step(logger, "执行采集", mode=mode.value)
        if mode == CrawlMode.DRISSION:
            pages = _run_drission_phase(task, session, crawl_step)
        elif mode == CrawlMode.SCRAPY:
            pages = _run_scrapy_phase(task, session, crawl_step)
        else:
            pages = _run_scrapy_phase(task, session, crawl_step)

        log_substep(
            logger,
            crawl_step,
            9,
            "采集阶段原始页数统计",
            page_count=len(pages),
        )

        llm_step = log_step(
            logger,
            "LLM 字段 enrichment",
            prompt=bool(task.prompt),
            page_count=len(pages),
        )
        pages, llm_used = enrich_pages_with_llm(
            pages,
            task,
            parent_step=llm_step,
        )
        result.pages = pages
        result.llm_used = llm_used
        log_substep(
            logger,
            llm_step,
            9,
            "LLM enrichment 完成",
            llm_used=llm_used,
        )

    except Exception as exc:
        log_error(logger, "采集任务异常终止", error=str(exc))
        logger.exception("采集任务失败")
        result.errors.append(str(exc))

    result.finished_at = datetime.now(timezone.utc).isoformat()
    out_step = log_step(
        logger,
        "写入结果文件",
        output=task.output_path,
        meta=task.meta_path,
    )
    out_path, meta_path = write_result(result)
    log_substep(
        logger,
        out_step,
        1,
        "落盘完成",
        output=str(out_path),
        meta=str(meta_path),
        page_count=len(result.pages),
        error_count=len(result.errors),
    )

    log_done(
        logger,
        "采集任务结束",
        mode=result.mode_used.value,
        pages=len(result.pages),
        session_reused=result.session_reused,
        llm_used=result.llm_used,
        errors=len(result.errors),
    )
    return result
