"""把 Brief 渲染成 Markdown 报告与推送用的短摘要。"""

from __future__ import annotations

import datetime as dt
from collections import OrderedDict

from .models import Assessment, NewsItem
from .pipeline import CST, Brief

DISCLAIMER = (
    "本报告由脚本自动抓取公开数据生成，规则与阈值均写在 `advisor.py` 中，"
    "仅用于辅助自己做功课，不构成投资建议。数据源可能延迟或出错，下单前请自行复核。"
)


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2f}%"


def _num(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:,.{digits}f}"


def _pos(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}分位"


def _time(ts: int | None) -> str:
    if not ts:
        return ""
    return dt.datetime.fromtimestamp(ts, CST).strftime("%m-%d %H:%M")


def _news_line(item: NewsItem) -> str:
    stamp = _time(item.published_at)
    prefix = f"`{stamp}` " if stamp else ""
    title = f"[{item.title}]({item.url})" if item.url else item.title
    tags = "、".join(item.tags[:3])
    suffix = f" — {tags}" if tags else ""
    return f"{prefix}**{item.source}**：{title}{suffix}"


def _group(assessments: list[Assessment]) -> "OrderedDict[str, list[Assessment]]":
    grouped: OrderedDict[str, list[Assessment]] = OrderedDict()
    for item in assessments:
        grouped.setdefault(item.metrics.instrument.group, []).append(item)
    return grouped


def render_markdown(brief: Brief) -> str:
    lines: list[str] = []
    bench_name = brief.benchmark.instrument.name if brief.benchmark else "沪深300"

    lines.append(f"# 每日市场简报 {brief.date_label}")
    lines.append("")
    lines.append(f"生成时间：{brief.run_at:%Y-%m-%d %H:%M} (UTC+8)　|　行情日期：{brief.data_date or '未知'}")
    if brief.stale:
        lines.append("")
        lines.append(f"> 今日非交易日或行情尚未更新，以下数据为最近一个交易日（{brief.data_date}）的收盘情况。")
    lines.append("")

    lines += _section_overview(brief, bench_name)
    lines += _section_cn(brief, bench_name)
    lines += _section_global(brief, bench_name)
    lines += _section_news(brief)
    lines += _section_actions(brief)

    if brief.llm_summary:
        lines.append("## 六、AI 综述")
        lines.append("")
        lines.append(brief.llm_summary.strip())
        lines.append("")

    if brief.errors:
        lines.append("## 数据抓取告警")
        lines.append("")
        for err in dict.fromkeys(brief.errors):
            lines.append(f"- {err}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")
    return "\n".join(lines)


def _section_overview(brief: Brief, bench_name: str) -> list[str]:
    lines = ["## 一、今日速览", ""]
    view = brief.view
    if brief.benchmark:
        m = brief.benchmark
        lines.append(
            f"- **{bench_name}**：{_num(m.quote.price)}　今日 {_pct(m.ret.get('1d'))}　"
            f"近1周 {_pct(m.ret.get('1w'))}　近1月 {_pct(m.ret.get('1m'))}　"
            f"近3月 {_pct(m.ret.get('3m'))}　区间位置 {_pos(m.range_position)}"
        )
    if view:
        lines.append(f"- **市场温度**：{view.temperature}　|　**建议总仓位**：{view.suggested_position}")
        if view.breadth.get("合计"):
            b = view.breadth
            lines.append(f"- **观察池宽度**：A股标的 {b['上涨']} 涨 / {b['下跌']} 跌（共 {b['合计']} 个）")
        if view.leaders:
            top = "、".join(
                f"{a.metrics.instrument.name}({_pct(a.metrics.excess.get('1m'))})" for a in view.leaders[:3]
            )
            lines.append(f"- **近1月超额领先**：{top}")
        if view.laggards:
            weak = "、".join(
                f"{a.metrics.instrument.name}({_pct(a.metrics.excess.get('1m'))})" for a in view.laggards[:3]
            )
            lines.append(f"- **近1月明显落后**：{weak}")
        if view.reasons:
            lines.append("")
            lines.append("判断依据：")
            for reason in view.reasons:
                lines.append(f"- {reason}")
    lines.append("")
    return lines


def _section_cn(brief: Brief, bench_name: str) -> list[str]:
    lines = [f"## 二、A股板块ETF 与 {bench_name} 对比", ""]
    if not brief.cn_assessments:
        lines += ["（无数据）", ""]
        return lines
    for group, items in _group(brief.cn_assessments).items():
        lines.append(f"### {group}")
        lines.append("")
        lines.append("| 标的 | 最新价 | 今日 | 近1周 | 周超额 | 近1月 | 月超额 | 近3月 | 区间位置 | 趋势 | 建议 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        items = sorted(items, key=lambda a: -(a.metrics.excess.get("1m") or -999))
        for a in items:
            m = a.metrics
            lines.append(
                f"| {m.instrument.name} `{m.instrument.symbol}` | {_num(m.quote.price, 3)} | "
                f"{_pct(m.ret.get('1d'))} | {_pct(m.ret.get('1w'))} | {_pct(m.excess.get('1w'))} | "
                f"{_pct(m.ret.get('1m'))} | {_pct(m.excess.get('1m'))} | {_pct(m.ret.get('3m'))} | "
                f"{_pos(m.range_position)} | {a.trend} | {a.action} |"
            )
        lines.append("")
    return lines


def _section_global(brief: Brief, bench_name: str) -> list[str]:
    lines = ["## 三、全球市场", ""]
    if not brief.global_assessments:
        lines += ["（无数据）", ""]
        return lines
    for group, items in _group(brief.global_assessments).items():
        lines.append(f"### {group}")
        lines.append("")
        lines.append(f"| 标的 | 最新 | 今日 | 近1周 | 近1月 | 近3月 | 相对本地基准(近1月) | 相对{bench_name}(近1月) | 趋势 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for a in sorted(items, key=lambda x: -(x.metrics.ret.get("1m") or -999)):
            m = a.metrics
            lines.append(
                f"| {m.instrument.name} `{m.instrument.symbol}` | {_num(m.quote.price)} | "
                f"{_pct(m.ret.get('1d'))} | {_pct(m.ret.get('1w'))} | {_pct(m.ret.get('1m'))} | "
                f"{_pct(m.ret.get('3m'))} | {_pct(m.excess.get('1m'))} | {_pct(m.excess.get('cn_1m'))} | "
                f"{a.trend} |"
            )
        lines.append("")
    return lines


def _section_news(brief: Brief) -> list[str]:
    lines = ["## 四、资讯要点", ""]
    bundle = brief.news
    if not bundle.items:
        lines += ["（本次未获取到资讯）", ""]
        return lines

    lines.append(f"共抓取 {len(bundle.items)} 条去重后资讯，来源："
                 + "、".join(sorted({i.source.split('/')[0] for i in bundle.items})))
    lines.append("")

    lines.append("### 宏观与政策（高影响）")
    lines.append("")
    macro = sorted((i for i in bundle.items if any(t in bundle.macro_hits for t in i.tags)),
                   key=lambda i: (-i.importance, -(i.published_at or 0)))
    used = {id(i) for i in macro[:10]}
    if macro:
        for item in macro[:10]:
            lines.append(f"- {_news_line(item)}")
    else:
        lines.append("- 今日无明显政策/宏观级别消息")
    lines.append("")

    lines.append("### A股与国内消息")
    lines.append("")
    domestic = [i for i in bundle.top(80, scope="国内")
                if id(i) not in used and i.region in {"国内", "全球"}][:12]
    used |= {id(i) for i in domestic}
    for item in domestic:
        lines.append(f"- {_news_line(item)}")
    if not domestic:
        lines.append("- 无")
    lines.append("")

    lines.append("### 全球宏观")
    lines.append("")
    worldwide = [i for i in bundle.top(80, scope="海外")
                 if id(i) not in used and i.region in {"国内", "全球"}][:10]
    used |= {id(i) for i in worldwide}
    for item in worldwide:
        lines.append(f"- {_news_line(item)}")
    if not worldwide:
        lines.append("- 无")
    lines.append("")

    lines.append("### 海外市场")
    lines.append("")
    overseas_regions = {"美股", "港股", "日本", "韩国", "泰国", "东南亚", "欧洲"}
    any_overseas = False
    for region in sorted(overseas_regions):
        items = [i for i in bundle.top(6, region=region) if id(i) not in used][:4]
        if not items:
            continue
        used |= {id(i) for i in items}
        any_overseas = True
        lines.append(f"**{region}**")
        lines.append("")
        for item in items:
            lines.append(f"- {_news_line(item)}")
        lines.append("")
    if not any_overseas:
        lines += ["- 无", ""]
    return lines


def _section_actions(brief: Brief) -> list[str]:
    lines = ["## 五、操作建议与理由", ""]
    view = brief.view
    if view:
        lines.append(f"**组合层面**：{view.temperature}，建议总仓位 {view.suggested_position}")
        lines.append("")

    ranked = sorted(brief.cn_assessments, key=lambda a: -a.score)
    actionable = [a for a in ranked if a.action != "观望，等信号"]
    show = actionable if actionable else ranked[:6]

    for a in show:
        m = a.metrics
        lines.append(f"### {m.instrument.name} `{m.instrument.symbol}` — {a.action}")
        lines.append("")
        lines.append(f"- 评分 {a.score:+.2f}　趋势：{a.trend}　强弱：{a.strength}")
        lines.append(f"- 今日 {_pct(m.ret.get('1d'))}　近1周 {_pct(m.ret.get('1w'))}（超额 {_pct(m.excess.get('1w'))}）"
                     f"　近1月 {_pct(m.ret.get('1m'))}（超额 {_pct(m.excess.get('1m'))}）")
        if a.reasons:
            lines.append("- 理由：")
            for reason in a.reasons:
                lines.append(f"  - {reason}")
        if a.signals:
            lines.append("- 信号：" + "；".join(a.signals))
        if a.related_news:
            lines.append("- 相关消息：")
            for item in a.related_news[:3]:
                lines.append(f"  - {_news_line(item)}")
        lines.append("")

    skipped = [a for a in ranked if a not in show]
    if skipped:
        lines.append("其余标的暂列观望：" + "、".join(
            f"{a.metrics.instrument.name}({a.score:+.1f})" for a in skipped))
        lines.append("")

    lines += _global_notes(brief)
    return lines


def _global_notes(brief: Brief) -> list[str]:
    """海外与大类资产只做提示，不给具体买卖动作。"""
    notable = [a for a in brief.global_assessments
               if abs(a.metrics.ret.get("1d") or 0) >= 1.5 or abs(a.metrics.ret.get("1w") or 0) >= 3]
    if not notable:
        return []
    notable.sort(key=lambda a: -(abs(a.metrics.ret.get("1d") or 0)))
    lines = ["### 海外与大类资产提示", ""]
    for a in notable[:8]:
        m = a.metrics
        lines.append(
            f"- **{m.instrument.name}**（{m.instrument.market}）今日 {_pct(m.ret.get('1d'))}，"
            f"近1周 {_pct(m.ret.get('1w'))}，近1月 {_pct(m.ret.get('1m'))}，{a.trend}；"
            f"相对沪深300近1月 {_pct(m.excess.get('cn_1m'))}"
        )
    lines.append("")
    return lines


def render_digest(brief: Brief, max_items: int = 6) -> str:
    """推送用的精简版（微信/Telegram 卡片）。"""
    parts: list[str] = [f"【{brief.date_label} 市场简报】"]
    if brief.benchmark:
        m = brief.benchmark
        parts.append(f"{m.instrument.name}: 今日 {_pct(m.ret.get('1d'))}, 近1周 {_pct(m.ret.get('1w'))}, "
                     f"近1月 {_pct(m.ret.get('1m'))}")
    if brief.view:
        parts.append(f"温度: {brief.view.temperature} | 建议仓位: {brief.view.suggested_position}")

    ranked = sorted(brief.cn_assessments, key=lambda a: -a.score)
    if ranked:
        parts.append("")
        parts.append("重点关注:")
        for a in ranked[:max_items]:
            parts.append(f"· {a.metrics.instrument.name} {_pct(a.metrics.ret.get('1d'))} "
                         f"(月超额 {_pct(a.metrics.excess.get('1m'))}) → {a.action}")
    top_news = brief.news.top(4)
    if top_news:
        parts.append("")
        parts.append("要闻:")
        for item in top_news:
            parts.append(f"· [{item.source}] {item.title}")
    return "\n".join(parts)
