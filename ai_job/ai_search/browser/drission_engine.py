"""有头浏览器：人机协同登录、会话导出、单页 HTML 获取。"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from ai_search.constants import DEFAULT_REQUEST_HEADERS
from ai_search.models import SessionSnapshot
from ai_search.step_log import log_phase, log_substep, log_warn

logger = logging.getLogger(__name__)


def _import_chromium_page():
    try:
        from DrissionPage import ChromiumPage
    except ImportError as exc:
        raise ImportError(
            "未安装 DrissionPage。请执行: pip install DrissionPage"
        ) from exc
    return ChromiumPage


def open_page_headed(
    url: str,
    *,
    headless: bool = False,
    parent_step: int | None = None,
) -> Any:
    """打开页面并返回 ChromiumPage 实例（调用方负责 close）。"""
    log_phase(
        logger,
        "BROWSER",
        "启动浏览器实例",
        url=url,
        headless=headless,
    )
    ChromiumPage = _import_chromium_page()
    page = ChromiumPage()
    if hasattr(page, "set") and hasattr(page.set, "headless"):
        page.set.headless(headless)
    page.get(url)
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            "browser-open",
            "浏览器导航完成",
            url=url,
            headless=headless,
        )
    else:
        log_phase(logger, "BROWSER", "浏览器导航完成", url=url, headless=headless)
    return page


def _normalize_cookies(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [
            {"name": k, "value": str(v), "domain": "", "path": "/"}
            for k, v in raw.items()
        ]
    if isinstance(raw, list):
        out: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict) and "name" in item:
                out.append(dict(item))
        return out
    return []


def export_session_from_browser(
    page: Any,
    *,
    site_id: str,
    source_url: str,
    ttl_hours: int = 24,
    parent_step: int | None = None,
) -> SessionSnapshot:
    """从当前浏览器上下文导出会话快照。"""
    log_phase(
        logger,
        "BROWSER",
        "开始导出浏览器会话",
        site_id=site_id,
        source_url=source_url,
    )
    cookies: list[dict[str, Any]] = []
    if hasattr(page, "cookies") and callable(page.cookies):
        raw = page.cookies()
        cookies = _normalize_cookies(raw)
    elif hasattr(page, "get_cookies"):
        cookies = _normalize_cookies(page.get_cookies())

    user_agent = DEFAULT_REQUEST_HEADERS.get("User-Agent", "")
    try:
        if hasattr(page, "run_js"):
            ua = page.run_js("return navigator.userAgent")
            if ua:
                user_agent = str(ua)
    except Exception as exc:
        log_warn(logger, "BROWSER", "读取 userAgent 失败", error=str(exc))

    expires = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    snapshot = SessionSnapshot(
        site_id=site_id,
        source_url=source_url,
        cookies=cookies,
        headers={"User-Agent": user_agent},
        user_agent=user_agent,
        expires_at=expires.isoformat(),
    )
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            "browser-export",
            "会话快照构建完成",
            cookie_count=len(cookies),
            expires_at=snapshot.expires_at,
        )
    else:
        log_phase(
            logger,
            "BROWSER",
            "会话快照构建完成",
            cookie_count=len(cookies),
            expires_at=snapshot.expires_at,
        )
    return snapshot


def _wait_user_confirm(
    *,
    login_wait_seconds: int,
    message: str,
    parent_step: int | None = None,
) -> None:
    import sys

    print(message)
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            "browser-wait",
            "等待用户完成登录",
            login_wait_seconds=login_wait_seconds,
            interactive=sys.stdin.isatty(),
        )
    if login_wait_seconds > 0:
        print(f"将在 {login_wait_seconds} 秒后自动继续（未交互时）...")
        try:
            import select

            if sys.stdin.isatty():
                r, _, _ = select.select([sys.stdin], [], [], login_wait_seconds)
                if r:
                    sys.stdin.readline()
                    if parent_step is not None:
                        log_substep(logger, parent_step, "browser-wait", "用户确认继续（Enter）")
                    return
        except Exception:
            pass
        time.sleep(login_wait_seconds)
        if parent_step is not None:
            log_substep(logger, parent_step, "browser-wait", "等待超时，自动继续")
        return
    if sys.stdin.isatty():
        input("完成后按 Enter 继续采集…")
        if parent_step is not None:
            log_substep(logger, parent_step, "browser-wait", "用户确认继续（Enter）")
    else:
        log_warn(logger, "BROWSER", "非交互终端，默认等待 30 秒")
        time.sleep(30)


def interactive_login(
    url: str,
    *,
    site_id: str,
    login_wait_seconds: int = 0,
    ttl_hours: int = 24,
    parent_step: int | None = None,
) -> SessionSnapshot:
    """有头打开 URL，等待用户完成登录后导出 session。"""
    page = open_page_headed(url, headless=False, parent_step=parent_step)
    try:
        _wait_user_confirm(
            login_wait_seconds=login_wait_seconds,
            message=(
                f"\n请在已打开的浏览器中完成登录/验证：\n  {url}\n"
                f"站点标识: {site_id}\n"
            ),
            parent_step=parent_step,
        )
        current = getattr(page, "url", None) or url
        if callable(current):
            current = page.url
        if parent_step is not None:
            log_substep(
                logger,
                parent_step,
                "browser-url",
                "登录后当前页面",
                current_url=str(current),
            )
        return export_session_from_browser(
            page,
            site_id=site_id,
            source_url=str(current),
            ttl_hours=ttl_hours,
            parent_step=parent_step,
        )
    finally:
        log_phase(logger, "BROWSER", "关闭浏览器实例")
        try:
            page.quit()
        except Exception as exc:
            log_warn(logger, "BROWSER", "关闭浏览器失败", error=str(exc))


def capture_page_html(
    url: str,
    *,
    session: SessionSnapshot | None = None,
    parent_step: int | None = None,
    sub_step: int | str | None = None,
) -> str:
    """使用浏览器加载页面并返回 HTML（可注入 cookie）。"""
    label = sub_step if sub_step is not None else "capture"
    if parent_step is not None:
        log_substep(
            logger,
            parent_step,
            label,
            "浏览器抓取页面 HTML",
            url=url,
            inject_session=bool(session),
        )
    page = open_page_headed(url, headless=True)
    try:
        if session and session.cookies and hasattr(page, "set") and hasattr(page.set, "cookies"):
            try:
                page.set.cookies(session.cookies)
                if parent_step is not None:
                    log_substep(
                        logger,
                        parent_step,
                        f"{label}-cookies",
                        "已注入会话 Cookies",
                        count=len(session.cookies),
                    )
            except Exception as exc:
                log_warn(logger, "BROWSER", "注入 cookies 失败", error=str(exc))
        page.get(url)
        html = ""
        if hasattr(page, "html"):
            html = str(page.html)
        elif hasattr(page, "get_html"):
            html = str(page.get_html())
        if parent_step is not None:
            log_substep(
                logger,
                parent_step,
                f"{label}-done",
                "HTML 抓取完成",
                html_len=len(html),
            )
        return html
    finally:
        try:
            page.quit()
        except Exception:
            pass


def derive_site_id(url: str) -> str:
    host = urlparse(url).netloc or "unknown"
    return host.replace(":", "_")
