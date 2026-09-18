"""通用 RSS 解析：CNBC / Yahoo Finance / Investing.com / Google News。"""

from __future__ import annotations

import datetime as dt
import email.utils
import re
import urllib.parse
import xml.etree.ElementTree as ET

from ..http import Http
from ..models import NewsItem

GOOGLE_NEWS_URL = "https://news.google.com/rss/search"
_TAG_RE = re.compile(r"<[^>]+>")
_SOURCE_SUFFIX_RE = re.compile(r"\s+-\s+[^-]{2,30}$")


def _clean(text: str | None) -> str:
    return _TAG_RE.sub("", text or "").replace("&nbsp;", " ").strip()


def _parse_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp())


def parse_feed(xml_text: str, source: str, limit: int, region: str, weight: int,
               strip_source_suffix: bool = False) -> list[NewsItem]:
    root = ET.fromstring(xml_text.strip())
    items: list[NewsItem] = []
    for node in root.iter("item"):
        title = _clean(node.findtext("title"))
        if not title:
            continue
        publisher = ""
        if strip_source_suffix:
            match = _SOURCE_SUFFIX_RE.search(title)
            if match:
                publisher = match.group(0).lstrip(" -")
                title = title[: match.start()].strip()
        items.append(NewsItem(
            title=title,
            source=f"{source}/{publisher}" if publisher else source,
            published_at=_parse_date(node.findtext("pubDate")),
            summary=_clean(node.findtext("description"))[:240],
            url=(node.findtext("link") or "").strip(),
            region=region,
            importance=weight,
        ))
        if len(items) >= limit:
            break
    return items


def fetch(http: Http, url: str, name: str, limit: int = 20, region: str = "全球",
          weight: int = 2) -> list[NewsItem]:
    return parse_feed(http.get_text(url, encoding="utf-8"), name, limit, region, weight)


def fetch_google_news(http: Http, query: str, name: str, limit: int = 10, region: str = "全球",
                      weight: int = 2, hl: str = "zh-CN", gl: str = "CN",
                      ceid: str = "CN:zh-Hans") -> list[NewsItem]:
    url = f"{GOOGLE_NEWS_URL}?{urllib.parse.urlencode({'q': query, 'hl': hl, 'gl': gl, 'ceid': ceid})}"
    return parse_feed(http.get_text(url, encoding="utf-8"), name, limit, region, weight,
                      strip_source_suffix=True)
