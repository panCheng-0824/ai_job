from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from online_search.search_answer_config import (
    AD_DOMAIN_BLOCKLIST,
    AD_KEYWORDS,
    TRACKING_QUERY_KEYS,
)


def normalize_url(url: str) -> str:
    parsed = urlparse(url or "")
    query_items = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_QUERY_KEYS
    ]
    new_query = urlencode(query_items, doseq=True)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def is_ad_link(title: str, url: str, snippet: str = "") -> bool:
    blocked, _ = classify_link(title=title, url=url, snippet=snippet)
    return blocked


def classify_link(title: str, url: str, snippet: str = "") -> tuple[bool, str]:
    parsed = urlparse(url or "")
    host = (parsed.netloc or "").lower()
    if not host:
        return True, "empty-host"

    if any(host == blocked or host.endswith(f".{blocked}") for blocked in AD_DOMAIN_BLOCKLIST):
        return True, f"domain-blocked:{host}"

    text = f"{title or ''} {snippet or ''}".lower()
    hits = sum(1 for kw in AD_KEYWORDS if kw.lower() in text)
    if hits >= 2:
        return True, f"keyword-hits:{hits}"
    return False, "ok"
