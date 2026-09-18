"""指标计算：区间涨跌、相对基准超额、均线、区间位置、波动与回撤。"""

from __future__ import annotations

import math
from statistics import fmean, pstdev

from .models import Bar, Instrument, Metrics, Quote

# 窗口名 -> 回看的交易日数量
WINDOWS: dict[str, int] = {"1d": 1, "1w": 5, "1m": 20, "3m": 60}
WINDOW_LABELS: dict[str, str] = {"1d": "今日", "1w": "近1周", "1m": "近1月", "3m": "近3月"}
RANGE_LOOKBACK = 120
MA_PERIODS = (20, 60)


def build_series(bars: list[Bar], quote: Quote | None) -> list[Bar]:
    """把最新报价并入日K序列，保证序列末尾就是当日数据。"""
    series = sorted(bars, key=lambda b: b.date)
    if quote is None:
        return series
    if not series:
        return [Bar(date=quote.trade_date or "", open=quote.open or quote.price, close=quote.price,
                    high=quote.high or quote.price, low=quote.low or quote.price, volume=0.0)]
    last = series[-1]
    trade_date = quote.trade_date
    if trade_date and trade_date > last.date:
        series.append(Bar(date=trade_date, open=quote.open or quote.price, close=quote.price,
                          high=quote.high or quote.price, low=quote.low or quote.price, volume=0.0))
    elif trade_date and trade_date == last.date:
        series[-1] = Bar(date=last.date, open=last.open, close=quote.price,
                         high=max(last.high, quote.price), low=min(last.low, quote.price),
                         volume=last.volume)
    return series


def window_return(closes: list[float], days: int) -> float | None:
    """`days` 个交易日的累计涨跌幅（%）。数据不足时用最长可用区间。"""
    if len(closes) < 2:
        return None
    span = min(days, len(closes) - 1)
    base = closes[-1 - span]
    if not base:
        return None
    return (closes[-1] / base - 1) * 100


def sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return fmean(closes[-period:])


def range_position(closes: list[float], lookback: int = RANGE_LOOKBACK) -> float | None:
    """当前价在近 `lookback` 个交易日高低区间中的位置（0=最低，100=最高）。"""
    window = closes[-lookback:]
    if len(window) < 10:
        return None
    low, high = min(window), max(window)
    if high <= low:
        return None
    return (window[-1] - low) / (high - low) * 100


def annualized_volatility(closes: list[float], period: int = 20) -> float | None:
    window = closes[-(period + 1):]
    if len(window) < 6:
        return None
    rets = [window[i] / window[i - 1] - 1 for i in range(1, len(window)) if window[i - 1]]
    if len(rets) < 5:
        return None
    return pstdev(rets) * math.sqrt(250) * 100


def max_drawdown(closes: list[float], lookback: int = 60) -> float | None:
    window = closes[-lookback:]
    if len(window) < 5:
        return None
    peak = window[0]
    worst = 0.0
    for value in window:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1)
    return worst * 100


def volume_ratio(series: list[Bar], period: int = 20) -> float | None:
    """当日成交量与前 `period` 日均量之比；盘中成交量为 0 时返回 None。"""
    if len(series) < period + 1:
        return None
    today = series[-1].volume
    if not today:
        return None
    baseline = fmean([b.volume for b in series[-(period + 1):-1]])
    if not baseline:
        return None
    return today / baseline


def returns_of(series: list[Bar], quote: Quote | None) -> dict[str, float | None]:
    closes = [b.close for b in series]
    out: dict[str, float | None] = {}
    for name, days in WINDOWS.items():
        out[name] = window_return(closes, days)
    # 当日涨跌以实时报价的前收盘为准，比K线更可靠（除权、盘中未收盘等情况）
    if quote is not None and quote.change_pct is not None:
        out["1d"] = quote.change_pct
    return out


def compute_metrics(instrument: Instrument, quote: Quote, bars: list[Bar],
                    benchmark_returns: dict[str, float | None] | None = None,
                    cross_returns: dict[str, float | None] | None = None,
                    history_proxy: str | None = None,
                    merge_quote: bool = True) -> Metrics:
    # 用代理标的算历史时不能再并入本体报价，否则最后两根K线会指向同一天
    series = build_series(bars, quote) if merge_quote else sorted(bars, key=lambda b: b.date)
    closes = [b.close for b in series]
    ret = returns_of(series, quote)

    excess: dict[str, float | None] = {}
    if benchmark_returns:
        for name in WINDOWS:
            mine, bench = ret.get(name), benchmark_returns.get(name)
            excess[name] = None if mine is None or bench is None else mine - bench
    if cross_returns:
        for name in WINDOWS:
            mine, bench = ret.get(name), cross_returns.get(name)
            excess[f"cn_{name}"] = None if mine is None or bench is None else mine - bench

    ma = {p: sma(closes, p) for p in MA_PERIODS}
    bias = {}
    for period, value in ma.items():
        bias[period] = None if not value else (closes[-1] / value - 1) * 100

    return Metrics(
        instrument=instrument,
        quote=quote,
        ret=ret,
        excess=excess,
        ma=ma,
        ma_bias=bias,
        range_position=range_position(closes),
        volume_ratio=volume_ratio(series),
        volatility=annualized_volatility(closes),
        max_drawdown=max_drawdown(closes),
        bars_used=len(series),
        history_proxy=history_proxy,
    )
