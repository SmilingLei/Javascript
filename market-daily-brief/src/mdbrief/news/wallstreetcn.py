"""华尔街见闻实时快讯（全球宏观、中文）。"""

from __future__ import annotations

import re

from ..http import Http
from ..models import NewsItem

URL = "https://api-one.wallstcn.com/apiv1/content/lives"
_TAG_RE = re.compile(r"<[^>]+>")
_BRACKET_RE = re.compile(r"^【(.{2,40}?)】")


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text or "").replace("&nbsp;", " ").strip()


def fetch(http: Http, limit: int = 30, region: str = "全球", weight: int = 4) -> list[NewsItem]:
    payload = http.get_json(URL, params={"channel": "global-channel", "limit": min(limit, 100)})
    rows = ((payload.get("data") or {}).get("items")) or []

    items: list[NewsItem] = []
    for row in rows[:limit]:
        title = _clean(row.get("title") or "")
        text = _clean(row.get("content_text") or row.get("content") or "")
        if not title:
            head = _BRACKET_RE.match(text)
            title = head.group(1) if head else text[:70]
        if not title:
            continue
        importance = weight + (2 if row.get("score", 0) and int(row.get("score") or 0) >= 1 else 0)
        items.append(NewsItem(
            title=title,
            source="华尔街见闻",
            published_at=int(row.get("display_time") or 0) or None,
            summary=text if text != title else "",
            url=(row.get("uri") or ""),
            tags=[t.get("name") for t in (row.get("asset_tags") or []) if isinstance(t, dict) and t.get("name")],
            region=region,
            importance=importance,
        ))
    return items
