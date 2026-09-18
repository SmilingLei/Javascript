"""腾讯财经行情：A股/港股实时快照与日K线。

实时接口 qt.gtimg.cn 返回 GBK 编码的 `v_<code>="f1~f2~..."` 文本，字段按位置解析。
"""

from __future__ import annotations

import logging
import re

from ..http import Http
from ..models import Bar, Quote

log = logging.getLogger(__name__)

QUOTE_URL = "https://qt.gtimg.cn/q={codes}"
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

# qt.gtimg.cn 实时字段位置（0 起）
IDX_NAME = 1
IDX_CODE = 2
IDX_PRICE = 3
IDX_PREV_CLOSE = 4
IDX_OPEN = 5
IDX_TIME = 30
IDX_HIGH = 33
IDX_LOW = 34
IDX_TURNOVER = 37  # 成交额，单位万元
IDX_TURNOVER_RATE = 38

_LINE_RE = re.compile(r'v_([^=]+)="([^"]*)"')
_BATCH_SIZE = 40


def normalize_symbol(symbol: str) -> str:
    """把 `510300` 之类的裸代码补全成腾讯要求的 `sh510300`。"""
    code = symbol.strip().lower()
    if code[:2] in {"sh", "sz", "bj", "hk", "us"}:
        return code
    if not code.isdigit():
        return code
    if code[0] in {"5", "6", "9"}:
        return f"sh{code}"
    if code[0] in {"4", "8"}:
        return f"bj{code}"
    return f"sz{code}"


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(raw: str) -> str | None:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


def fetch_quotes(http: Http, symbols: list[str]) -> dict[str, Quote]:
    """批量拉取实时行情，key 为归一化后的代码。"""
    result: dict[str, Quote] = {}
    codes = [normalize_symbol(s) for s in symbols]
    for start in range(0, len(codes), _BATCH_SIZE):
        chunk = codes[start:start + _BATCH_SIZE]
        text = http.get_text(QUOTE_URL.format(codes=",".join(chunk)), encoding="gbk")
        for code, payload in _LINE_RE.findall(text):
            fields = payload.split("~")
            if len(fields) < 35:
                continue
            price = _to_float(fields[IDX_PRICE])
            prev_close = _to_float(fields[IDX_PREV_CLOSE])
            if price is None or prev_close is None or price <= 0:
                continue
            result[code] = Quote(
                symbol=code,
                name=fields[IDX_NAME] or code,
                price=price,
                prev_close=prev_close,
                open=_to_float(fields[IDX_OPEN]),
                high=_to_float(fields[IDX_HIGH]),
                low=_to_float(fields[IDX_LOW]),
                turnover=_to_float(fields[IDX_TURNOVER]) if len(fields) > IDX_TURNOVER else None,
                turnover_rate=_to_float(fields[IDX_TURNOVER_RATE]) if len(fields) > IDX_TURNOVER_RATE else None,
                trade_date=_parse_time(fields[IDX_TIME]) if len(fields) > IDX_TIME else None,
                currency="CNY" if code.startswith(("sh", "sz", "bj")) else None,
                provider="tencent",
            )
    return result


def fetch_kline(http: Http, symbol: str, bars: int = 130) -> list[Bar]:
    code = normalize_symbol(symbol)
    payload = http.get_json(
        KLINE_URL,
        params={"param": f"{code},day,,,{bars},qfq", "_var": ""},
    )
    data = (payload.get("data") or {}).get(code) or {}
    rows = data.get("qfqday") or data.get("day") or []
    out: list[Bar] = []
    for row in rows:
        if len(row) < 6:
            continue
        try:
            out.append(Bar(date=row[0], open=float(row[1]), close=float(row[2]),
                           high=float(row[3]), low=float(row[4]), volume=float(row[5])))
        except (TypeError, ValueError):
            continue
    return out
