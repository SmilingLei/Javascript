"""财联社电报（cls.cn）。

开放接口需要 sign 参数：把请求参数按 key 排序后做 urlencode，先 sha1 再 md5 即为签名。
返回项自带 plate_list / stock_list / subjects，用于板块与个股关联。
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse

from ..http import Http
from ..models import NewsItem

ROLL_URL = "https://www.cls.cn/v1/roll/get_roll_list"
BASE_PARAMS = {"app": "CailianpressWeb", "os": "web", "sv": "8.4.6"}
_TAG_RE = re.compile(r"<[^>]+>")


def _sign(params: dict[str, str]) -> str:
    query = urllib.parse.urlencode(sorted(params.items()))
    return hashlib.md5(hashlib.sha1(query.encode()).hexdigest().encode()).hexdigest()


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text or "").replace("&nbsp;", " ").strip()


PAGE_SIZE = 50  # rn 超过 50 服务端会直接返回空列表


def _page(http: Http, size: int, last_time: int | None) -> list[dict]:
    params = dict(BASE_PARAMS, rn=str(size))
    if last_time:
        params["last_time"] = str(last_time)
    url = f"{ROLL_URL}?{urllib.parse.urlencode(sorted(params.items()))}&sign={_sign(params)}"
    payload = http.get_json(url, headers={"Referer": "https://www.cls.cn/telegraph"}, encoding="utf-8")
    return ((payload.get("data") or {}).get("roll_data")) or []


def fetch(http: Http, limit: int = 60, region: str = "国内", weight: int = 5) -> list[NewsItem]:
    rows: list[dict] = []
    last_time: int | None = None
    while len(rows) < limit:
        page = _page(http, min(PAGE_SIZE, limit - len(rows)), last_time)
        if not page:
            break
        rows.extend(page)
        last_time = int(page[-1].get("ctime") or 0) or None
        if not last_time:
            break

    items: list[NewsItem] = []
    for row in rows[:limit]:
        # ad 字段始终是个占位对象，只有 is_ad / is_fad 才代表真的是广告
        if str(row.get("is_ad") or "0") != "0" or str(row.get("is_fad") or "0") != "0":
            continue
        title = _clean(row.get("title") or "")
        brief = _clean(row.get("brief") or row.get("content") or "")
        if not title:
            # 短电报没有标题，取正文首句；财联社正文统一以“财联社X月X日电，”开头
            body = re.sub(r"^财联社\d+月\d+日电[，,]\s*", "", brief)
            title = body[:70]
        if not title:
            continue
        tags = [t.get("subject_name") for t in (row.get("subjects") or []) if t.get("subject_name")]
        tags += [p.get("plate_name") for p in (row.get("plate_list") or []) if p.get("plate_name")]
        tags += [s.get("name") for s in (row.get("stock_list") or []) if s.get("name")]
        # level A/B 为财联社标记的重要电报
        level_bonus = {"A": 3, "B": 2}.get(str(row.get("level") or ""), 0)
        items.append(NewsItem(
            title=title,
            source="财联社",
            published_at=int(row.get("ctime") or 0) or None,
            summary=brief if brief != title else "",
            url=f"https://www.cls.cn/detail/{row.get('id')}" if row.get("id") else "",
            tags=[t for t in dict.fromkeys(tags) if t],
            region=region,
            importance=weight + level_bonus,
        ))
    return items
