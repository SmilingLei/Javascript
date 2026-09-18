"""资讯聚合：并发抓取多源、去重、打分，并与观察列表做关联。"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from ..config import Config, NewsSource
from ..http import Http
from ..models import Instrument, NewsItem
from . import cls, rss, sina, ths, wallstreetcn

log = logging.getLogger(__name__)

MAX_WORKERS = 8
FRESH_HOURS = 36

# 各家快讯内容高度重合，去重时优先保留信息质量更高、带板块标签的源
SOURCE_PRIORITY = {"财联社": 5, "同花顺": 4, "华尔街见闻": 3, "新浪7x24": 2, "新浪财经": 2}

# 同一条快讯各家措辞不同，标题二元组相似度超过该阈值就视为重复
SIMILARITY_THRESHOLD = 0.62

CN_WORDS = (
    "中国", "央行", "人民银行", "国务院", "发改委", "财政部", "证监会", "银保监", "国资委", "工信部",
    "商务部", "统计局", "国常会", "政治局", "A股", "沪指", "深指", "上证", "深证", "创业板", "科创",
    "北交所", "沪深", "人民币", "北向", "南向", "两融", "港股", "港交所", "内地", "北京", "上海",
    "深圳", "广东", "浙江", "江苏", "国产", "国内",
)
OVERSEAS_WORDS = (
    "美联储", "美国", "特朗普", "白宫", "欧盟", "欧洲", "欧央行", "欧洲央行", "德国", "法国", "英国",
    "日本", "日央行", "韩国", "泰国", "印尼", "越南", "新加坡", "俄罗斯", "乌克兰", "以色列", "伊朗",
    "中东", "纳斯达克", "标普", "道指", "LME", "OPEC", "IMF", "华尔街",
)


@dataclass
class NewsBundle:
    items: list[NewsItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    macro_hits: dict[str, list[NewsItem]] = field(default_factory=dict)
    by_symbol: dict[str, list[NewsItem]] = field(default_factory=dict)
    sentiment: dict[str, int] = field(default_factory=dict)

    def top(self, n: int = 12, region: str | None = None, scope: str | None = None) -> list[NewsItem]:
        pool = [i for i in self.items
                if (region is None or i.region == region) and (scope is None or i.scope == scope)]
        return sorted(pool, key=lambda i: (-i.importance, -(i.published_at or 0)))[:n]


def _fetch_one(http: Http, source: NewsSource) -> tuple[list[NewsItem], str | None]:
    opts = source.options
    try:
        if source.id == "cls":
            return cls.fetch(http, source.limit, source.region, source.weight), None
        if source.id == "ths":
            return ths.fetch(http, source.limit, source.region, source.weight), None
        if source.id == "wallstreetcn":
            return wallstreetcn.fetch(http, source.limit, source.region, source.weight), None
        if source.id == "sina_7x24":
            return sina.fetch_7x24(http, source.limit, source.region, source.weight), None
        if source.id == "sina_roll":
            return sina.fetch_roll(http, source.limit, source.region, source.weight), None
        if source.id == "rss":
            return rss.fetch(http, opts["url"], source.name, source.limit, source.region,
                             source.weight), None
        if source.id == "google_news":
            return rss.fetch_google_news(
                http, opts["query"], source.name, source.limit, source.region, source.weight,
                hl=opts.get("hl", "zh-CN"), gl=opts.get("gl", "CN"),
                ceid=opts.get("ceid", "CN:zh-Hans")), None
        return [], f"未知资讯源类型: {source.id}"
    except Exception as exc:  # noqa: BLE001 - 单源失败不影响整体
        return [], f"{source.name} 抓取失败: {exc}"


def collect(http: Http, config: Config, instruments: list[Instrument],
            fresh_hours: int = FRESH_HOURS) -> NewsBundle:
    bundle = NewsBundle()
    sources = [s for s in config.news_sources if s.enabled]
    if not sources:
        return bundle

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for items, err in pool.map(lambda s: _fetch_one(http, s), sources):
            if err:
                log.warning("%s", err)
                bundle.errors.append(err)
            bundle.items.extend(items)

    now = time.time()
    fresh: list[NewsItem] = []
    for item in bundle.items:
        # 地区源更新频率低，放宽时效窗口，否则泰国、东南亚这类分区经常整天空白
        hours = fresh_hours if item.region in {"国内", "全球", "美股"} else max(fresh_hours, 120)
        if item.published_at and item.published_at < now - hours * 3600:
            continue
        if item.dedup_key():
            fresh.append(item)
    bundle.items = _dedup(fresh)

    for item in bundle.items:
        item.scope = _classify_scope(item)
    _score_macro(bundle, config)
    _link_instruments(bundle, config, instruments)
    bundle.items.sort(key=lambda i: (-i.importance, -(i.published_at or 0)))
    return bundle


def _rank(item: NewsItem) -> tuple[int, int]:
    return SOURCE_PRIORITY.get(item.source.split("/")[0], 1), item.importance


def similarity(a: NewsItem, b: NewsItem) -> float:
    sa, sb = a.shingles(), b.shingles()
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _dedup(items: list[NewsItem]) -> list[NewsItem]:
    """先按标题精确去重，再做一轮近似去重（同一条快讯各家措辞不同）。"""
    exact: dict[str, NewsItem] = {}
    for item in items:
        key = item.dedup_key()
        current = exact.get(key)
        if current is None or _rank(item) > _rank(current):
            exact[key] = item

    ordered = sorted(exact.values(), key=lambda i: (-_rank(i)[0], -(i.published_at or 0)))
    kept: list[tuple[NewsItem, set[str]]] = []
    for item in ordered:
        shingles = item.shingles()
        if not shingles:
            continue
        if any(len(shingles & other) / len(shingles | other) >= SIMILARITY_THRESHOLD
               for _, other in kept):
            continue
        kept.append((item, shingles))
    return [item for item, _ in kept]


def _classify_scope(item: NewsItem) -> str:
    """按内容判断是国内还是海外消息，来源国籍并不可靠（财联社也大量报海外）。"""
    text = _text_of(item)
    cn = sum(1 for w in CN_WORDS if w in text)
    overseas = sum(1 for w in OVERSEAS_WORDS if w in text)
    if cn and cn >= overseas:
        return "国内"
    if overseas:
        return "海外"
    return "国内" if item.region == "国内" else "海外"


def _text_of(item: NewsItem) -> str:
    return f"{item.title} {item.summary} {' '.join(item.tags)}"


def _score_macro(bundle: NewsBundle, config: Config) -> None:
    now = time.time()
    for item in bundle.items:
        text = _text_of(item)
        hits: list[str] = []
        for category, words in config.macro_keywords.items():
            if any(word in text for word in words):
                hits.append(category)
        if hits:
            item.importance += min(2 * len(hits), 4)
            item.tags = list(dict.fromkeys(item.tags + hits))
            for category in hits:
                bundle.macro_hits.setdefault(category, []).append(item)
        if item.published_at and now - item.published_at <= 12 * 3600:
            item.importance += 1


def _link_instruments(bundle: NewsBundle, config: Config, instruments: list[Instrument]) -> None:
    positive = config.sentiment.get("positive", [])
    negative = config.sentiment.get("negative", [])
    for inst in instruments:
        if not inst.keywords:
            continue
        related: list[NewsItem] = []
        score = 0
        for item in bundle.items:
            text = _text_of(item)
            matched = [kw for kw in inst.keywords if kw and kw in text]
            if not matched:
                continue
            item.matched = list(dict.fromkeys(item.matched + [inst.name]))
            related.append(item)
            score += sum(1 for w in positive if w in text)
            score -= sum(1 for w in negative if w in text)
        if related:
            related.sort(key=lambda i: (-i.importance, -(i.published_at or 0)))
            bundle.by_symbol[inst.symbol] = related[:6]
            bundle.sentiment[inst.symbol] = score
