"""同花顺快讯（news.10jqka.com.cn）。"""

from __future__ import annotations

import re

from ..http import Http
from ..models import NewsItem

URL = "https://news.10jqka.com.cn/tapp/news/push/stock/"
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text or "").replace("&nbsp;", " ").strip()


def fetch(http: Http, limit: int = 40, region: str = "国内", weight: int = 4) -> list[NewsItem]:
    payload = http.get_json(URL, params={"page": 1, "tag": "", "track": "website",
                                         "pagesize": min(limit, 100)},
                            headers={"Referer": "https://news.10jqka.com.cn/realtimenews.html"})
    rows = ((payload.get("data") or {}).get("list")) or []

    items: list[NewsItem] = []
    for row in rows[:limit]:
        title = _clean(row.get("title") or "")
        if not title:
            continue
        tags = [t.get("name") for t in (row.get("tagInfo") or []) if isinstance(t, dict) and t.get("name")]
        if isinstance(row.get("tags"), str) and row["tags"]:
            tags += [t for t in re.split(r"[,，;；/]", row["tags"]) if t]
        stock = row.get("stock")
        if isinstance(stock, list):
            tags += [s.get("name") for s in stock if isinstance(s, dict) and s.get("name")]
        # import 字段是同花顺自己的重要性标记
        importance = weight + (2 if str(row.get("import") or "0") not in {"0", "", "None"} else 0)
        items.append(NewsItem(
            title=title,
            source="同花顺",
            published_at=int(row.get("ctime") or 0) or None,
            summary=_clean(row.get("digest") or ""),
            url=row.get("url") or row.get("shareUrl") or "",
            tags=[t for t in dict.fromkeys(tags) if t],
            region=region,
            importance=importance,
        ))
    return items
