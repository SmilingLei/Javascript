import json

from mdbrief.providers import tencent, yahoo

# 取自 qt.gtimg.cn 的真实返回（截断了买卖档之外的尾部字段）
TENCENT_LINE = (
    'v_sh510300="1~沪深300ETF华泰柏瑞~510300~4.582~4.532~4.556~6297211~3436640~2860571~'
    "4.581~57097~4.580~23250~4.579~7791~4.578~3323~4.577~1104~"
    "4.582~8638~4.583~11641~4.584~6276~4.585~15727~4.586~4926~~"
    '20260918161452~0.050~1.10~4.596~4.548~4.582/6297211/2877462543~6297211~287746~2.66~~~"'
)


class FakeHttp:
    def __init__(self, text: str = "", payload=None):
        self._text = text
        self._payload = payload

    def get_text(self, *a, **kw) -> str:
        return self._text

    def get_json(self, *a, **kw):
        return self._payload


def test_normalize_symbol_infers_exchange():
    assert tencent.normalize_symbol("510300") == "sh510300"
    assert tencent.normalize_symbol("159915") == "sz159915"
    assert tencent.normalize_symbol("833171") == "bj833171"
    assert tencent.normalize_symbol("sh000300") == "sh000300"
    assert tencent.normalize_symbol("HSTECH.HK") == "hstech.hk"


def test_tencent_quote_parsing():
    quotes = tencent.fetch_quotes(FakeHttp(TENCENT_LINE), ["510300"])
    quote = quotes["sh510300"]
    assert quote.name == "沪深300ETF华泰柏瑞"
    assert quote.price == 4.582
    assert quote.prev_close == 4.532
    assert quote.trade_date == "2026-09-18"
    assert round(quote.change_pct, 2) == 1.10


def test_tencent_kline_parsing():
    payload = {"data": {"sh510300": {"qfqday": [
        ["2026-09-17", "4.539", "4.532", "4.568", "4.524", "5075461.000"],
        ["2026-09-18", "4.556", "4.582", "4.596", "4.548", "6297211.000"],
    ]}}}
    rows = tencent.fetch_kline(FakeHttp(payload=payload), "510300")
    assert [b.date for b in rows] == ["2026-09-17", "2026-09-18"]
    assert rows[-1].close == 4.582


def _chart(price, market_time, stamps, closes, chart_prev=None):
    return {"chart": {"result": [{
        "meta": {"regularMarketPrice": price, "regularMarketTime": market_time,
                 "gmtoffset": 28800, "shortName": "TEST", "currency": "HKD",
                 "chartPreviousClose": chart_prev},
        "timestamp": stamps,
        "indicators": {"quote": [{"close": closes, "open": closes, "high": closes,
                                  "low": closes, "volume": [1] * len(closes)}]},
    }]}}


def test_yahoo_prev_close_ignores_chart_previous_close():
    # 2026-09-17 09:30 与 2026-09-18 09:30 (UTC+8)；当日K线还没落库(close=None)
    payload = _chart(24750.78, 1789719000, [1789608600, 1789695000], [24604.28, None],
                     chart_prev=26025.42)
    quote, bars = yahoo.fetch(FakeHttp(payload=payload), "^HSI")
    assert quote.trade_date == "2026-09-18"
    assert quote.prev_close == 24604.28
    assert round(quote.change_pct, 2) == 0.60
    assert len(bars) == 1


def test_yahoo_prev_close_when_today_bar_present():
    payload = _chart(26410.30, 1789719000, [1789608600, 1789695000], [26418.30, 26410.30])
    quote, _ = yahoo.fetch(FakeHttp(payload=payload), "^IXIC")
    assert quote.prev_close == 26418.30
    assert quote.change_pct < 0


def test_yahoo_sparse_series_falls_back_to_chart_previous_close():
    payload = _chart(1584.15, 1789719000, [1789695000], [1584.15], chart_prev=1583.34)
    quote, _ = yahoo.fetch(FakeHttp(payload=payload), "^SET.BK")
    assert quote.prev_close == 1583.34


def test_yahoo_raises_on_error_payload():
    import pytest

    with pytest.raises(ValueError):
        yahoo.fetch(FakeHttp(payload={"chart": {"result": [], "error": "Not Found"}}), "^BAD")


def test_json_roundtrip_of_fake_payload_is_stable():
    payload = _chart(1.0, 1789719000, [1789695000], [1.0])
    assert json.loads(json.dumps(payload)) == payload
