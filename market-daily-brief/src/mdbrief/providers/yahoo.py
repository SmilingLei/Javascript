"""Yahoo Finance chart 接口：覆盖港股、美股、日韩、东南亚、欧洲指数与商品汇率。

只用 /v8/finance/chart/<symbol>，一次请求同时拿到最新报价与日K线，无需 cookie/crumb。
"""

from __future__ import annotations

import datetime as dt
import logging
from urllib.parse import quote

from ..http import Http
from ..models import Bar, Quote

log = logging.getLogger(__name__)

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _session_date(meta: dict, bars: list[Bar]) -> str | None:
    """当前交易日：优先用 regularMarketTime（当日K线可能还没落库）。"""
    stamp = meta.get("regularMarketTime")
    if stamp:
        offset = meta.get("gmtoffset") or 0
        return dt.datetime.fromtimestamp(stamp + offset, dt.timezone.utc).strftime("%Y-%m-%d")
    return bars[-1].date if bars else None


def _extract(payload: dict) -> tuple[dict, list[Bar]]:
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise ValueError(str(chart["error"]))
    results = chart.get("result") or []
    if not results:
        raise ValueError("Yahoo 返回空结果")
    result = results[0]
    meta = result.get("meta") or {}
    stamps = result.get("timestamp") or []
    quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quotes.get("close") or []
    opens = quotes.get("open") or []
    highs = quotes.get("high") or []
    lows = quotes.get("low") or []
    volumes = quotes.get("volume") or []

    tz_offset = meta.get("gmtoffset") or 0
    bars: list[Bar] = []
    for i, stamp in enumerate(stamps):
        close = closes[i] if i < len(closes) else None
        if close is None:
            continue
        date = dt.datetime.fromtimestamp(stamp + tz_offset, dt.timezone.utc).strftime("%Y-%m-%d")
        bars.append(Bar(
            date=date,
            open=float(opens[i]) if i < len(opens) and opens[i] is not None else float(close),
            close=float(close),
            high=float(highs[i]) if i < len(highs) and highs[i] is not None else float(close),
            low=float(lows[i]) if i < len(lows) and lows[i] is not None else float(close),
            volume=float(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0.0,
        ))
    return meta, bars


def fetch(http: Http, symbol: str, *, range_: str = "6mo") -> tuple[Quote, list[Bar]]:
    payload = http.get_json(CHART_URL.format(symbol=quote(symbol, safe="")),
                            params={"range": range_, "interval": "1d", "includePrePost": "false"})
    meta, bars = _extract(payload)

    price = meta.get("regularMarketPrice")
    if price is None and bars:
        price = bars[-1].close
    if price is None:
        raise ValueError(f"{symbol} 无最新价")

    trade_date = _session_date(meta, bars)
    # chartPreviousClose 是“区间起点之前”的收盘价，不是昨收，只能在没有历史K线时兜底
    prev_close: float | None = None
    if trade_date:
        earlier = [b for b in bars if b.date < trade_date]
        if earlier:
            prev_close = earlier[-1].close
    if prev_close is None and len(bars) >= 2:
        prev_close = bars[-2].close
    if prev_close is None:
        prev_close = meta.get("chartPreviousClose")

    quote_obj = Quote(
        symbol=symbol,
        name=meta.get("shortName") or meta.get("symbol") or symbol,
        price=float(price),
        prev_close=float(prev_close) if prev_close else None,
        high=meta.get("regularMarketDayHigh"),
        low=meta.get("regularMarketDayLow"),
        trade_date=trade_date,
        currency=meta.get("currency"),
        provider="yahoo",
    )
    return quote_obj, bars
