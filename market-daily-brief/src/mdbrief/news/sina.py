"""新浪财经：7x24 全球直播快讯 + 财经要闻滚动。"""

from __future__ import annotations

import re

from ..http import Http
from ..models import NewsItem

ZHIBO_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"
ROLL_URL = "https://feed.mix.sina.com.cn/api/roll/get"
_TAG_RE = re.compile(r"<[^>]+>")
_BRACKET_RE = re.compile(r"^【(.{2,40}?)】")


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text or "").replace("&nbsp;", " ").strip()


def fetch_7x24(http: Http, limit: int = 40, region: str = "全球", weight: int = 3) -> list[NewsItem]:
    payload = http.get_json(ZHIBO_URL, params={"page": 1, "page_size": min(limit, 100),
                                               "zhibo_id": 152, "tag_id": 0, "dire": "f", "dpc": 1})
    rows = (((payload.get("result") or {}).get("data") or {}).get("feed") or {}).get("list") or []

    items: list[NewsItem] = []
    for row in rows[:limit]:
        text = _clean(row.get("rich_text") or row.get("content") or "")
        if not text:
            continue
        head = _BRACKET_RE.match(text)
        title = head.group(1) if head else text[:70]
        tags = [t.get("name") for t in (row.get("tag") or []) if isinstance(t, dict) and t.get("name")]
        items.append(NewsItem(
            title=title,
            source="新浪7x24",
            published_at=_ts(row.get("create_time")),
            summary=text if text != title else "",
            url=row.get("docurl") or "",
            tags=[t for t in dict.fromkeys(tags) if t],
            region=region,
            importance=weight,
        ))
    return items


def fetch_roll(http: Http, limit: int = 25, region: str = "国内", weight: int = 3) -> list[NewsItem]:
    payload = http.get_json(ROLL_URL, params={"pageid": 155, "lid": 1686, "num": min(limit, 50), "page": 1})
    rows = ((payload.get("result") or {}).get("data")) or []

    items: list[NewsItem] = []
    for row in rows[:limit]:
        title = _clean(row.get("title") or "")
        if not title:
            continue
        items.append(NewsItem(
            title=title,
            source="新浪财经",
            published_at=int(row.get("ctime") or 0) or None,
            summary=_clean(row.get("intro") or row.get("summary") or ""),
            url=row.get("url") or "",
            tags=[k for k in re.split(r"[,，;；]", row.get("keywords") or "") if k][:6],
            region=region,
            importance=weight,
        ))
    return items


def _ts(value: object) -> int | None:
    """新浪 create_time 形如 '2026-09-19 01:20:33'。"""
    if not value:
        return None
    import datetime as dt

    try:
        naive = dt.datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        return int(naive.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).timestamp())
    except ValueError:
        return None
