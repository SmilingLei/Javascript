import datetime as dt

from mdbrief import advisor, report
from mdbrief.models import Instrument, Metrics, NewsItem, Quote
from mdbrief.news import NewsBundle
from mdbrief.pipeline import CST, Brief


def build_assessment(symbol, name, market="A股", group="宽基指数", month_excess=4.0):
    instrument = Instrument(symbol=symbol, name=name, market=market, group=group)
    quote = Quote(symbol=symbol, name=name, price=4.5, prev_close=4.45)
    metrics = Metrics(instrument=instrument, quote=quote)
    metrics.ret = {"1d": 1.12, "1w": 2.0, "1m": 5.0, "3m": -3.0}
    metrics.excess = {"1w": 1.0, "1m": month_excess, "cn_1m": month_excess}
    metrics.ma = {20: 4.3, 60: 4.1}
    metrics.ma_bias = {20: 4.6, 60: 9.7}
    metrics.range_position = 62.0
    return advisor.assess(metrics, "沪深300")


def build_brief() -> Brief:
    bench = build_assessment("sh000300", "沪深300", month_excess=0.0).metrics
    brief = Brief(run_at=dt.datetime(2026, 9, 18, 16, 40, tzinfo=CST), benchmark=bench)
    brief.cn_assessments = [
        build_assessment("sh512480", "半导体ETF", group="科技成长", month_excess=6.0),
        build_assessment("sh512800", "银行ETF", group="金融周期", month_excess=-5.0),
    ]
    brief.global_assessments = [
        build_assessment("^HSI", "恒生指数", market="港股", group="港股", month_excess=-1.0),
    ]
    brief.news = NewsBundle(items=[
        NewsItem(title="央行宣布降准", source="财联社", region="国内", scope="国内",
                 importance=8, tags=["政策货币"], url="https://example.com/a"),
        NewsItem(title="美联储官员表态", source="华尔街见闻", region="全球", scope="海外",
                 importance=6, url="https://example.com/b"),
    ])
    brief.news.macro_hits = {"政策货币": [brief.news.items[0]]}
    brief.data_date = "2026-09-18"
    brief.view = advisor.market_view(bench, brief.all_assessments, brief.news.macro_hits)
    return brief


def test_markdown_contains_all_sections():
    text = report.render_markdown(build_brief())
    for heading in ["# 每日市场简报 2026-09-18（周五）", "## 一、今日速览",
                    "## 二、A股板块ETF 与 沪深300 对比", "## 三、全球市场",
                    "## 四、资讯要点", "## 五、操作建议与理由"]:
        assert heading in text
    assert "半导体ETF" in text and "恒生指数" in text
    assert "不构成投资建议" in text


def test_markdown_tables_are_well_formed():
    text = report.render_markdown(build_brief())
    rows = [line for line in text.splitlines() if line.startswith("| ")]
    assert rows
    widths = {len(row.split("|")) for row in rows}
    # 表头、分隔行与数据行的列数必须一致，否则 Markdown 渲染会错位
    assert len(widths) == 2


def test_stale_data_is_flagged():
    brief = build_brief()
    brief.stale = True
    assert "非交易日或行情尚未更新" in report.render_markdown(brief)


def test_digest_is_short_and_actionable():
    digest = report.render_digest(build_brief())
    assert "市场简报" in digest
    assert "半导体ETF" in digest
    assert len(digest) < 1200
    assert "要闻" in digest


def test_errors_are_surfaced():
    brief = build_brief()
    brief.errors = ["Yahoo 获取失败 ^BAD: 404", "Yahoo 获取失败 ^BAD: 404"]
    text = report.render_markdown(brief)
    assert "## 数据抓取告警" in text
    # 重复告警只展示一次
    assert text.count("Yahoo 获取失败 ^BAD: 404") == 1
