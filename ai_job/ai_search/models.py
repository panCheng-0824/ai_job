"""采集任务、会话快照与结果的数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CrawlMode(str, Enum):
    """采集模式。"""

    AUTO = "auto"
    HYBRID = "hybrid"
    SCRAPY = "scrapy"
    DRISSION = "drission"


@dataclass
class SessionSnapshot:
    """浏览器导出的会话，供 Scrapy 注入。"""

    site_id: str
    source_url: str
    cookies: list[dict[str, Any]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    local_storage: dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: str | None = None

    def cookie_dict(self) -> dict[str, str]:
        """转为 Scrapy Request 可用的 name -> value 字典。"""
        out: dict[str, str] = {}
        for item in self.cookies:
            name = item.get("name")
            value = item.get("value")
            if name and value is not None:
                out[str(name)] = str(value)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "source_url": self.source_url,
            "cookies": self.cookies,
            "headers": self.headers,
            "local_storage": self.local_storage,
            "user_agent": self.user_agent,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSnapshot:
        return cls(
            site_id=str(data.get("site_id") or ""),
            source_url=str(data.get("source_url") or ""),
            cookies=list(data.get("cookies") or []),
            headers=dict(data.get("headers") or {}),
            local_storage=dict(data.get("local_storage") or {}),
            user_agent=str(data.get("user_agent") or ""),
            created_at=str(data.get("created_at") or ""),
            expires_at=data.get("expires_at"),
        )


@dataclass
class CrawlTask:
    """一次采集任务参数。"""

    url: str
    prompt: str = ""
    mode: CrawlMode = CrawlMode.HYBRID
    require_login: bool = False
    site_id: str = ""
    max_pages: int = 10
    follow_links: bool = False
    reuse_session: bool = True
    force_relogin: bool = False
    login_wait_seconds: int = 0
    output_path: str = "ai_search/output.json"
    meta_path: str = "ai_search/meta.json"
    # 可选：手工指定列表项链接 CSS，跳过后续 LLM 猜链接
    link_selector: str = ""
    # 可选：字段级 CSS 选择器 {"title": "h1", "price": ".price"}
    field_selectors: dict[str, str] = field(default_factory=dict)
    # 模型档位：空则读 AI_SEARCH_MODEL_LEVEL 或默认 mid（见 modelCfg.json）
    model_level: str = ""

    def resolved_site_id(self) -> str:
        if self.site_id:
            return self.site_id
        from urllib.parse import urlparse

        host = urlparse(self.url).netloc or "unknown"
        return host.replace(":", "_")


@dataclass
class PageRecord:
    """单页采集结果。"""

    url: str
    title: str = ""
    body: str = ""
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawlResult:
    """任务最终结果。"""

    task: CrawlTask
    mode_used: CrawlMode
    pages: list[PageRecord] = field(default_factory=list)
    session_reused: bool = False
    llm_used: bool = False
    errors: list[str] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finished_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.task.url,
            "prompt": self.task.prompt,
            "mode_used": self.mode_used.value,
            "session_reused": self.session_reused,
            "llm_used": self.llm_used,
            "errors": self.errors,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "pages": [
                {
                    "url": p.url,
                    "title": p.title,
                    "body": p.body[:2000] if p.body else "",
                    "fields": p.fields,
                }
                for p in self.pages
            ],
        }
