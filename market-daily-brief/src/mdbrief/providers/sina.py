"""新浪行情：A股实时快照与日K线，作为腾讯接口的备用源。"""

from __future__ import annotations

import logging
import re

from ..http import Http
from ..models import Bar, Quote
from .tencent import normalize_symbol

log = logging.getLogger(__name__)

QUOTE_URL = "https://hq.sinajs.cn/list={codes}"
KLINE_URL = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
             "CN_MarketData.getKLineData")
HEADERS = {"Referer": "https://finance.sina.com.cn"}

_LINE_RE = re.compile(r'var hq_str_([^=]+)="([^"]*)"')


def fetch_quotes(http: Http, symbols: list[str]) -> dict[str, Quote]:
    codes = [normalize_symbol(s) for s in symbols]
    if not codes:
        return {}
    text = http.get_text(QUOTE_URL.format(codes=",".join(codes)), headers=HEADERS, encoding="gbk")
    out: dict[str, Quote] = {}
    for code, payload in _LINE_RE.findall(text):
        fields = payload.split(",")
        if len(fields) < 32:
            continue
        try:
            price = float(fields[3])
            prev_close = float(fields[2])
        except ValueError:
            continue
        if price <= 0:
            continue
        out[code] = Quote(
            symbol=code,
            name=fields[0],
            price=price,
            prev_close=prev_close,
            open=float(fields[1]) if fields[1] else None,
            high=float(fields[4]) if fields[4] else None,
            low=float(fields[5]) if fields[5] else None,
            turnover=float(fields[9]) / 1e4 if fields[9] else None,
            trade_date=fields[30] or None,
            currency="CNY",
            provider="sina",
        )
    return out


def fetch_kline(http: Http, symbol: str, bars: int = 130) -> list[Bar]:
    code = normalize_symbol(symbol)
    rows = http.get_json(KLINE_URL, headers=HEADERS,
                         params={"symbol": code, "scale": 240, "ma": "no", "datalen": bars})
    out: list[Bar] = []
    for row in rows or []:
        try:
            out.append(Bar(date=str(row["day"])[:10], open=float(row["open"]), close=float(row["close"]),
                           high=float(row["high"]), low=float(row["low"]), volume=float(row["volume"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out
