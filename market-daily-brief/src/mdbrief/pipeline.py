"""编排：抓行情 + 抓资讯 -> 计算指标 -> 生成结论。"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from . import advisor, analysis
from .config import Config
from .http import Http
from .models import Assessment, Bar, Instrument, Metrics
from .news import NewsBundle, collect
from .providers import fetch_market_data

log = logging.getLogger(__name__)

CST = dt.timezone(dt.timedelta(hours=8))
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


@dataclass
class Brief:
    run_at: dt.datetime
    benchmark: Metrics | None
    benchmarks: dict[str, Metrics] = field(default_factory=dict)
    cn_assessments: list[Assessment] = field(default_factory=list)
    global_assessments: list[Assessment] = field(default_factory=list)
    view: advisor.MarketView | None = None
    news: NewsBundle = field(default_factory=NewsBundle)
    errors: list[str] = field(default_factory=list)
    data_date: str | None = None
    stale: bool = False
    llm_summary: str | None = None

    @property
    def date_label(self) -> str:
        return f"{self.run_at:%Y-%m-%d}（{WEEKDAYS[self.run_at.weekday()]}）"

    @property
    def all_assessments(self) -> list[Assessment]:
        return self.cn_assessments + self.global_assessments


def _metrics_for(instrument: Instrument, data, bench_ret=None, cross_ret=None) -> Metrics | None:
    quote = data.quote(instrument.symbol)
    if quote is None:
        return None
    bars = data.kline(instrument.history_key)
    proxy = instrument.history_symbol if (instrument.history_symbol and bars) else None
    if proxy:
        # 代理标的价格量级不同，等比缩放到本体价位，这样均线/区间位置才有可比性；涨跌幅不受缩放影响
        scale = quote.price / bars[-1].close if bars[-1].close else 1.0
        bars = [Bar(date=b.date, open=b.open * scale, close=b.close * scale,
                    high=b.high * scale, low=b.low * scale, volume=b.volume) for b in bars]
    return analysis.compute_metrics(instrument, quote, bars, bench_ret, cross_ret,
                                    history_proxy=proxy, merge_quote=proxy is None)


def build_brief(config: Config, *, http: Http | None = None, skip_news: bool = False,
                fresh_hours: int = 36) -> Brief:
    own_http = http is None
    http = http or Http()
    run_at = dt.datetime.now(CST)
    brief = Brief(run_at=run_at, benchmark=None)

    try:
        bench_instruments = config.benchmark_instruments()
        data = fetch_market_data(http, bench_instruments + config.instruments)
        brief.errors.extend(data.errors)

        bench_metrics: dict[str, Metrics] = {}
        for key, bench in config.benchmarks.items():
            inst = bench.as_instrument()
            metrics = _metrics_for(inst, data)
            if metrics is None:
                brief.errors.append(f"基准 {bench.name}({bench.symbol}) 行情缺失")
                continue
            bench_metrics[key] = metrics
        brief.benchmarks = bench_metrics

        cross = config.cross_reference
        cross_ret = bench_metrics[cross.key].ret if cross and cross.key in bench_metrics else None
        main_key = cross.key if cross else next(iter(bench_metrics), None)
        brief.benchmark = bench_metrics.get(main_key) if main_key else None
        if brief.benchmark:
            brief.data_date = brief.benchmark.quote.trade_date
            brief.stale = bool(brief.data_date and brief.data_date != f"{run_at:%Y-%m-%d}")

        news = NewsBundle() if skip_news else collect(http, config, config.instruments, fresh_hours)
        brief.news = news
        brief.errors.extend(news.errors)

        for inst in config.instruments:
            bench = config.benchmark(inst.benchmark) or cross
            bench_ret = bench_metrics[bench.key].ret if bench and bench.key in bench_metrics else None
            use_cross = cross_ret if (cross and inst.market != "A股") else None
            metrics = _metrics_for(inst, data, bench_ret, use_cross)
            if metrics is None:
                brief.errors.append(f"{inst.name}({inst.symbol}) 行情缺失，已跳过")
                continue
            assessment = advisor.assess(
                metrics,
                bench.name if bench else "基准",
                sentiment=news.sentiment.get(inst.symbol, 0),
                related_news=news.by_symbol.get(inst.symbol, []),
            )
            if inst.market == "A股":
                brief.cn_assessments.append(assessment)
            else:
                brief.global_assessments.append(assessment)

        brief.view = advisor.market_view(brief.benchmark, brief.all_assessments, news.macro_hits)
    finally:
        if own_http:
            http.close()
    return brief
