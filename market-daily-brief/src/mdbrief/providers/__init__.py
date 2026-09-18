"""行情抓取门面：按 provider 分派，并在失败时降级到备用源。"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from ..http import Http
from ..models import Bar, Instrument, Quote
from . import sina, tencent, yahoo

log = logging.getLogger(__name__)

MAX_WORKERS = 8


@dataclass
class MarketData:
    quotes: dict[str, Quote] = field(default_factory=dict)
    bars: dict[str, list[Bar]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def quote(self, symbol: str) -> Quote | None:
        return self.quotes.get(symbol) or self.quotes.get(tencent.normalize_symbol(symbol))

    def kline(self, symbol: str) -> list[Bar]:
        return self.bars.get(symbol) or self.bars.get(tencent.normalize_symbol(symbol)) or []


def _history_symbols(instruments: list[Instrument]) -> dict[str, str]:
    """标的代码 -> 用于取历史K线的代码。"""
    return {inst.symbol: inst.history_key for inst in instruments}


def fetch_market_data(http: Http, instruments: list[Instrument], *, bars: int = 130) -> MarketData:
    data = MarketData()
    tencent_insts = [i for i in instruments if i.provider == "tencent"]
    yahoo_insts = [i for i in instruments if i.provider == "yahoo"]
    unknown = [i for i in instruments if i.provider not in {"tencent", "yahoo"}]
    for inst in unknown:
        data.errors.append(f"{inst.name}({inst.symbol}) 使用了未知数据源 {inst.provider}")

    if tencent_insts:
        _load_tencent(http, tencent_insts, data, bars)
    if yahoo_insts:
        _load_yahoo(http, yahoo_insts, data)
    return data


def _load_tencent(http: Http, instruments: list[Instrument], data: MarketData, bars: int) -> None:
    symbols = [i.symbol for i in instruments]
    try:
        quotes = tencent.fetch_quotes(http, symbols)
    except Exception as exc:  # noqa: BLE001
        log.warning("腾讯实时行情失败，降级新浪: %s", exc)
        data.errors.append(f"腾讯实时行情失败，已降级新浪: {exc}")
        quotes = {}

    missing = [s for s in symbols if tencent.normalize_symbol(s) not in quotes]
    if missing:
        try:
            quotes.update(sina.fetch_quotes(http, missing))
        except Exception as exc:  # noqa: BLE001
            data.errors.append(f"新浪实时行情失败: {exc}")
    data.quotes.update(quotes)

    for symbol in symbols:
        if tencent.normalize_symbol(symbol) not in data.quotes:
            data.errors.append(f"未取到实时行情: {symbol}")

    history = sorted(set(_history_symbols(instruments).values()))

    def load(symbol: str) -> tuple[str, list[Bar], str | None]:
        try:
            rows = tencent.fetch_kline(http, symbol, bars)
            if len(rows) < 2:
                rows = sina.fetch_kline(http, symbol, bars)
            return symbol, rows, None
        except Exception as exc:  # noqa: BLE001
            try:
                return symbol, sina.fetch_kline(http, symbol, bars), None
            except Exception as exc2:  # noqa: BLE001
                return symbol, [], f"K线获取失败 {symbol}: {exc} / {exc2}"

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for symbol, rows, err in pool.map(load, history):
            if err:
                data.errors.append(err)
            if rows:
                data.bars[tencent.normalize_symbol(symbol)] = rows


def _load_yahoo(http: Http, instruments: list[Instrument], data: MarketData) -> None:
    # 一次 chart 请求同时带回报价和K线，代理标的也只是多一个代码
    symbols = {i.symbol for i in instruments} | {i.history_key for i in instruments}

    def load(symbol: str) -> tuple[str, Quote | None, list[Bar], str | None]:
        try:
            quote, bars = yahoo.fetch(http, symbol)
            return symbol, quote, bars, None
        except Exception as exc:  # noqa: BLE001
            return symbol, None, [], f"Yahoo 获取失败 {symbol}: {exc}"

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for symbol, quote, bars, err in pool.map(load, sorted(symbols)):
            if err:
                data.errors.append(err)
                continue
            if quote:
                data.quotes[symbol] = quote
            if bars:
                data.bars[symbol] = bars
