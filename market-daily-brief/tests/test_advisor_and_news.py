from mdbrief import advisor
from mdbrief.config import Config, NewsSource, load_config
from mdbrief.models import Instrument, Metrics, NewsItem, Quote
from mdbrief.news import _classify_scope, _dedup, _link_instruments, _score_macro, NewsBundle


def make_metrics(**kwargs) -> Metrics:
    instrument = kwargs.pop("instrument", Instrument(symbol="sh512480", name="半导体ETF"))
    quote = kwargs.pop("quote", Quote(symbol="sh512480", name="半导体ETF", price=1.0, prev_close=1.0))
    metrics = Metrics(instrument=instrument, quote=quote)
    metrics.ret = kwargs.pop("ret", {})
    metrics.excess = kwargs.pop("excess", {})
    metrics.ma = kwargs.pop("ma", {20: None, 60: None})
    metrics.ma_bias = kwargs.pop("ma_bias", {20: None, 60: None})
    for key, value in kwargs.items():
        setattr(metrics, key, value)
    return metrics


def test_trend_classification():
    quote = Quote(symbol="x", name="x", price=110.0, prev_close=109.0)
    bull = make_metrics(quote=quote, ma={20: 105.0, 60: 100.0})
    assert advisor.classify_trend(bull) == advisor.TREND_BULL

    bear = make_metrics(quote=Quote(symbol="x", name="x", price=90.0, prev_close=91.0),
                        ma={20: 95.0, 60: 100.0})
    assert advisor.classify_trend(bear) == advisor.TREND_BEAR

    repair = make_metrics(quote=quote, ma={20: 105.0, 60: 115.0})
    assert advisor.classify_trend(repair) == advisor.TREND_REPAIR


def test_strong_outperformer_gets_add_action():
    metrics = make_metrics(
        quote=Quote(symbol="x", name="x", price=110.0, prev_close=108.0),
        ret={"1d": 1.85, "1w": 5.0, "1m": 8.0},
        excess={"1w": 3.0, "1m": 6.0},
        ma={20: 105.0, 60: 100.0},
        ma_bias={20: 4.7, 60: 10.0},
        range_position=70.0,
    )
    result = advisor.assess(metrics, "沪深300")
    assert result.action == advisor.ACTION_ADD
    assert result.trend == advisor.TREND_BULL
    assert any("跑赢" in reason for reason in result.reasons)


def test_overheated_leader_switches_to_trim_profit():
    metrics = make_metrics(
        quote=Quote(symbol="x", name="x", price=130.0, prev_close=126.0),
        ret={"1d": 3.2, "1w": 9.0, "1m": 20.0},
        excess={"1w": 6.0, "1m": 15.0},
        ma={20: 110.0, 60: 100.0},
        ma_bias={20: 18.0, 60: 30.0},
        range_position=99.0,
    )
    result = advisor.assess(metrics, "沪深300")
    assert result.action == advisor.ACTION_TRIM_PROFIT
    assert any("过热" in s for s in result.signals)


def test_weak_laggard_gets_reduce_action():
    metrics = make_metrics(
        quote=Quote(symbol="x", name="x", price=80.0, prev_close=81.0),
        ret={"1d": -1.2, "1w": -4.0, "1m": -12.0},
        excess={"1w": -3.5, "1m": -9.0},
        ma={20: 85.0, 60: 95.0},
        ma_bias={20: -5.9, 60: -15.8},
        range_position=5.0,
    )
    result = advisor.assess(metrics, "沪深300")
    assert result.action in {advisor.ACTION_REDUCE, advisor.ACTION_AVOID}
    assert result.score < 0


def test_index_tracking_etf_stays_neutral_in_weak_market():
    """跟踪基准的宽基在弱市里不该被判成减仓，超额接近 0 时应该是观望。"""
    metrics = make_metrics(
        quote=Quote(symbol="sh510300", name="沪深300ETF", price=4.582, prev_close=4.532),
        ret={"1d": 1.10, "1w": 0.07, "1m": -2.09},
        excess={"1w": 0.13, "1m": 0.32},
        ma={20: 4.6, 60: 4.8},
        ma_bias={20: -0.4, 60: -4.5},
        range_position=21.0,
    )
    assert advisor.assess(metrics, "沪深300").action == advisor.ACTION_WAIT


def test_market_view_positions_scale_with_breadth():
    strong = [
        advisor.assess(make_metrics(
            instrument=Instrument(symbol=f"sh{i}", name=f"ETF{i}"),
            quote=Quote(symbol=f"sh{i}", name=f"ETF{i}", price=110.0, prev_close=108.0),
            ret={"1d": 1.8, "1w": 4.0, "1m": 9.0}, excess={"1w": 2.0, "1m": 5.0},
            ma={20: 105.0, 60: 100.0}, ma_bias={20: 4.0, 60: 10.0}, range_position=60.0,
        ), "沪深300") for i in range(6)
    ]
    bench = make_metrics(quote=Quote(symbol="sh000300", name="沪深300", price=4600.0,
                                     prev_close=4550.0),
                         instrument=Instrument(symbol="sh000300", name="沪深300"),
                         ret={"1d": 1.1, "1w": 2.0, "1m": 6.0},
                         ma={20: 4400.0, 60: 4200.0}, ma_bias={20: 4.5, 60: 9.5},
                         range_position=80.0)
    view = advisor.market_view(bench, strong)
    assert view.temperature in {"偏热", "温和偏暖"}
    assert view.breadth["上涨"] == 6
    assert view.leaders


def test_news_dedup_prefers_higher_priority_source():
    items = [
        NewsItem(title="央行开展5000亿元MLF操作", source="新浪7x24", importance=3),
        NewsItem(title="央行开展5000亿元MLF操作", source="财联社", importance=5),
        NewsItem(title="央行开展5000亿元MLF操作净投放", source="同花顺", importance=4),
        NewsItem(title="完全不同的一条消息标题内容", source="同花顺", importance=4),
    ]
    kept = _dedup(items)
    assert len(kept) == 2
    assert kept[0].source == "财联社"


def test_scope_classification():
    assert _classify_scope(NewsItem(title="证监会就融资融券规则答记者问", source="财联社")) == "国内"
    assert _classify_scope(NewsItem(title="美联储官员支持9月加息", source="财联社")) == "海外"


def test_macro_scoring_and_instrument_linking():
    config = Config(
        benchmarks={}, instruments=[], news_sources=[],
        macro_keywords={"政策货币": ["降准", "降息"]},
        sentiment={"positive": ["利好", "上调"], "negative": ["下调"]},
    )
    bundle = NewsBundle(items=[
        NewsItem(title="央行宣布降准0.5个百分点，对银行板块构成利好", source="财联社", importance=5),
        NewsItem(title="某机构下调半导体行业评级", source="同花顺", importance=4),
    ])
    _score_macro(bundle, config)
    assert "政策货币" in bundle.macro_hits
    assert bundle.items[0].importance > 5

    instruments = [
        Instrument(symbol="sh512800", name="银行ETF", keywords=["银行"]),
        Instrument(symbol="sh512480", name="半导体ETF", keywords=["半导体"]),
    ]
    _link_instruments(bundle, config, instruments)
    assert bundle.sentiment["sh512800"] > 0
    assert bundle.sentiment["sh512480"] < 0
    assert bundle.by_symbol["sh512800"][0].title.startswith("央行")


def test_shipped_config_loads_and_is_consistent():
    config = load_config()
    assert len(config.instruments) > 40
    assert config.cross_reference is not None
    assert config.cross_reference.name == "沪深300"
    for inst in config.instruments:
        assert inst.provider in {"tencent", "yahoo"}
        if inst.benchmark:
            assert inst.benchmark in config.benchmarks
    assert any(s.id == "cls" for s in config.news_sources)
    assert isinstance(config.news_sources[0], NewsSource)
