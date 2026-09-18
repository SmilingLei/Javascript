"""数据模型：行情、资讯、分析结论。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Bar:
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float


@dataclass
class Quote:
    """某个标的最新一笔行情。"""

    symbol: str
    name: str
    price: float
    prev_close: float | None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    turnover: float | None = None
    turnover_rate: float | None = None
    trade_date: str | None = None
    currency: str | None = None
    provider: str | None = None

    @property
    def change_pct(self) -> float | None:
        if not self.prev_close:
            return None
        return (self.price / self.prev_close - 1) * 100


@dataclass
class Instrument:
    """观察列表中的一个标的。"""

    symbol: str
    name: str
    provider: str = "tencent"
    group: str = "其他"
    market: str = "A股"
    kind: str = "ETF"
    benchmark: str | None = None
    history_symbol: str | None = None
    keywords: list[str] = field(default_factory=list)
    note: str | None = None

    @property
    def history_key(self) -> str:
        return self.history_symbol or self.symbol


@dataclass
class NewsItem:
    title: str
    source: str
    published_at: int | None = None
    summary: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)
    region: str = "国内"
    scope: str = ""
    importance: int = 0
    matched: list[str] = field(default_factory=list)

    def dedup_key(self) -> str:
        cleaned = "".join(ch for ch in self.title if ch.isalnum())
        return cleaned[:40].lower()

    def shingles(self) -> set[str]:
        """标题的字符二元组，用于跨源的近似去重。"""
        cleaned = "".join(ch for ch in self.title if ch.isalnum())
        if len(cleaned) < 2:
            return {cleaned} if cleaned else set()
        return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


@dataclass
class Metrics:
    """单个标的的量化指标，涨跌幅单位均为百分比。"""

    instrument: Instrument
    quote: Quote
    ret: dict[str, float | None] = field(default_factory=dict)
    excess: dict[str, float | None] = field(default_factory=dict)
    ma: dict[int, float | None] = field(default_factory=dict)
    ma_bias: dict[int, float | None] = field(default_factory=dict)
    range_position: float | None = None
    volume_ratio: float | None = None
    volatility: float | None = None
    max_drawdown: float | None = None
    bars_used: int = 0
    history_proxy: str | None = None


@dataclass
class Assessment:
    """规则引擎给出的结论。"""

    metrics: Metrics
    trend: str
    strength: str
    signals: list[str] = field(default_factory=list)
    action: str = "观望"
    reasons: list[str] = field(default_factory=list)
    score: float = 0.0
    related_news: list[NewsItem] = field(default_factory=list)

