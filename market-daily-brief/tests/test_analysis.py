from pytest import approx

from mdbrief import analysis
from mdbrief.models import Bar, Instrument, Quote


def bars(closes, start_volume=1000.0):
    out = []
    for i, close in enumerate(closes):
        out.append(Bar(date=f"2026-01-{i + 1:02d}", open=close, close=close,
                       high=close * 1.01, low=close * 0.99, volume=start_volume))
    return out


def test_window_return_uses_longest_available_span():
    closes = [100.0, 110.0]
    assert analysis.window_return(closes, 1) == approx(10.0)
    # 数据不足 20 天时退化为可用的最长区间，而不是返回 None
    assert analysis.window_return(closes, 20) == approx(10.0)
    assert analysis.window_return([100.0], 1) is None


def test_sma_and_range_position():
    closes = [float(x) for x in range(1, 31)]
    assert analysis.sma(closes, 5) == 28.0
    assert analysis.sma(closes, 100) is None
    assert analysis.range_position(closes) == approx(100.0)
    assert analysis.range_position(list(reversed(closes))) == approx(0.0)


def test_build_series_appends_new_session():
    series = bars([10.0, 11.0])
    quote = Quote(symbol="sh510300", name="x", price=12.0, prev_close=11.0, trade_date="2026-01-03")
    merged = analysis.build_series(series, quote)
    assert len(merged) == 3
    assert merged[-1].close == 12.0


def test_build_series_replaces_same_session_close():
    series = bars([10.0, 11.0])
    quote = Quote(symbol="sh510300", name="x", price=11.5, prev_close=10.0, trade_date="2026-01-02")
    merged = analysis.build_series(series, quote)
    assert len(merged) == 2
    assert merged[-1].close == 11.5


def test_volume_ratio_detects_surge():
    series = bars([100.0] * 21)
    series[-1] = Bar(date=series[-1].date, open=100, close=100, high=101, low=99, volume=3000.0)
    assert analysis.volume_ratio(series) == approx(3.0)


def test_max_drawdown_is_negative_peak_to_trough():
    assert analysis.max_drawdown([100.0, 110.0, 120.0, 90.0, 95.0]) == approx(-25.0)
    # 样本太少时不给结论，避免用 3 根K线算回撤
    assert analysis.max_drawdown([100.0, 90.0]) is None


def test_compute_metrics_excess_versus_benchmark():
    instrument = Instrument(symbol="sh512480", name="半导体ETF")
    quote = Quote(symbol="sh512480", name="半导体ETF", price=110.0, prev_close=100.0,
                  trade_date="2026-01-06")
    history = bars([100.0, 100.0, 100.0, 100.0, 100.0])
    bench = {"1d": 2.0, "1w": 3.0, "1m": 1.0, "3m": None}
    metrics = analysis.compute_metrics(instrument, quote, history, bench)

    assert metrics.ret["1d"] == approx(10.0)
    assert metrics.excess["1d"] == approx(8.0)
    assert metrics.excess["1w"] == approx(7.0)
    assert metrics.excess["3m"] is None


def test_compute_metrics_without_quote_change_falls_back_to_kline():
    instrument = Instrument(symbol="^SET.BK", name="泰国SET", provider="yahoo")
    quote = Quote(symbol="^SET.BK", name="泰国SET", price=105.0, prev_close=None,
                  trade_date="2026-01-05")
    metrics = analysis.compute_metrics(instrument, quote, bars([100.0, 105.0]),
                                       history_proxy="THD", merge_quote=False)
    assert metrics.ret["1d"] == approx(5.0)
    assert metrics.history_proxy == "THD"
