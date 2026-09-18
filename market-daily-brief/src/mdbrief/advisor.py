"""规则引擎：把量化指标 + 消息面翻译成可执行的操作建议和理由。

所有判断都是公开规则，报告里会把触发的阈值和实际数值一起写出来，便于自行复核。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .analysis import WINDOW_LABELS
from .models import Assessment, Metrics, NewsItem

# 趋势
TREND_BULL = "多头排列"
TREND_REPAIR = "修复中"
TREND_RANGE = "震荡"
TREND_BEAR = "空头排列"

# 动作
ACTION_ADD = "持有 / 回调分批加仓"
ACTION_HOLD = "持有观察"
ACTION_TRIM_PROFIT = "持有但不追高，上移止盈"
ACTION_WAIT = "观望，等信号"
ACTION_REDUCE = "减仓或暂不参与"
ACTION_AVOID = "规避 / 逢反弹减仓"

# 阈值
VOL_SURGE = 1.8
VOL_SHRINK = 0.6
HIGH_POSITION = 85.0
LOW_POSITION = 20.0
OVERHEAT_BIAS = 10.0
HIGH_VOLATILITY = 45.0
DEEP_DRAWDOWN = -15.0
STRONG_EXCESS = 3.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fmt(value: float | None, unit: str = "%") -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}{unit}" if unit == "%" else f"{value:.2f}{unit}"


def classify_trend(metrics: Metrics) -> str:
    price = metrics.quote.price
    ma20, ma60 = metrics.ma.get(20), metrics.ma.get(60)
    if ma20 is None or ma60 is None:
        return TREND_RANGE
    if price > ma20 > ma60:
        return TREND_BULL
    if price < ma20 < ma60:
        return TREND_BEAR
    if price > ma20:
        return TREND_REPAIR
    return TREND_RANGE


def classify_strength(metrics: Metrics, benchmark_name: str) -> str:
    month = metrics.excess.get("1m")
    week = metrics.excess.get("1w")
    if month is None:
        return f"缺少足够历史，无法与{benchmark_name}比较"
    if month >= STRONG_EXCESS and (week or 0) >= 0:
        return f"显著强于{benchmark_name}"
    if month >= 0:
        return f"略强于{benchmark_name}"
    if month <= -STRONG_EXCESS:
        return f"显著弱于{benchmark_name}"
    return f"略弱于{benchmark_name}"


def assess(metrics: Metrics, benchmark_name: str, *, sentiment: int = 0,
           related_news: list[NewsItem] | None = None) -> Assessment:
    trend = classify_trend(metrics)
    strength = classify_strength(metrics, benchmark_name)
    signals: list[str] = []
    reasons: list[str] = []
    score = 0.0

    week_ex, month_ex = metrics.excess.get("1w"), metrics.excess.get("1m")
    if month_ex is not None:
        score += _clamp(month_ex, -10, 10) * 0.6
        reasons.append(
            f"近1月{'跑赢' if month_ex >= 0 else '跑输'}{benchmark_name} "
            f"{abs(month_ex):.2f} 个百分点（自身 {_fmt(metrics.ret.get('1m'))}）"
        )
    if week_ex is not None:
        score += _clamp(week_ex, -6, 6) * 0.8
        reasons.append(
            f"近1周{'跑赢' if week_ex >= 0 else '跑输'}{benchmark_name} "
            f"{abs(week_ex):.2f} 个百分点（自身 {_fmt(metrics.ret.get('1w'))}）"
        )

    if trend == TREND_BULL:
        score += 3
        reasons.append(f"价格站上20日与60日均线（MA20 {_fmt(metrics.ma.get(20), '')}，"
                       f"MA60 {_fmt(metrics.ma.get(60), '')}），中期趋势向上")
    elif trend == TREND_BEAR:
        score -= 3
        reasons.append("价格位于20日均线之下且均线下行，中期趋势仍偏弱")
    elif trend == TREND_REPAIR:
        score += 1
        reasons.append("价格重新站上20日均线，但60日均线尚未转向，属于修复阶段")

    bias20 = metrics.ma_bias.get(20)
    if bias20 is not None and bias20 > OVERHEAT_BIAS:
        score -= 2
        signals.append(f"短期过热：偏离MA20 {bias20:+.1f}%")

    position = metrics.range_position
    if position is not None:
        if position >= 95:
            score -= 2
            signals.append(f"处于近半年区间顶部（{position:.0f}分位）")
        elif position >= HIGH_POSITION:
            score -= 1
            signals.append(f"处于近半年区间高位（{position:.0f}分位）")
        elif position <= LOW_POSITION:
            signals.append(f"处于近半年区间低位（{position:.0f}分位）")
            if trend != TREND_BEAR:
                score += 1.5

    vr = metrics.volume_ratio
    if vr is not None:
        if vr >= VOL_SURGE:
            signals.append(f"放量（是20日均量的 {vr:.1f} 倍）")
            score += 1 if (metrics.ret.get("1d") or 0) > 0 else -1
        elif vr <= VOL_SHRINK:
            signals.append(f"缩量（仅为20日均量的 {vr:.1f} 倍）")

    day = metrics.ret.get("1d")
    if day is not None and abs(day) >= 3:
        signals.append(f"单日{'大涨' if day > 0 else '大跌'} {day:+.2f}%")

    if metrics.volatility is not None and metrics.volatility >= HIGH_VOLATILITY:
        score -= 1.5
        signals.append(f"年化波动率偏高（{metrics.volatility:.0f}%）")

    if metrics.max_drawdown is not None and metrics.max_drawdown <= DEEP_DRAWDOWN:
        signals.append(f"近3月最大回撤 {metrics.max_drawdown:.1f}%")

    if sentiment:
        score += _clamp(sentiment, -4, 4) * 0.5
        signals.append(f"消息面{'偏暖' if sentiment > 0 else '偏冷'}（情绪分 {sentiment:+d}）")

    action = _decide(score, position, bias20, trend)
    if metrics.history_proxy:
        signals.append(f"区间涨跌用代理标的 {metrics.history_proxy} 计算")

    return Assessment(metrics=metrics, trend=trend, strength=strength, signals=signals,
                      action=action, reasons=reasons, score=round(score, 2),
                      related_news=related_news or [])


def _decide(score: float, position: float | None, bias20: float | None, trend: str) -> str:
    overheated = (position is not None and position >= 95) or (bias20 is not None and bias20 > OVERHEAT_BIAS)
    if score >= 5:
        return ACTION_TRIM_PROFIT if overheated else ACTION_ADD
    if score >= 2:
        return ACTION_TRIM_PROFIT if overheated else ACTION_HOLD
    # 熊市里几乎所有标的都会吃到趋势扣分，观望区间放宽，避免把跟随大盘的宽基也判成减仓
    if score > -3:
        return ACTION_WAIT
    if score > -6:
        return ACTION_REDUCE
    return ACTION_AVOID


@dataclass
class MarketView:
    """大盘层面的温度与仓位建议。"""

    temperature: str
    suggested_position: str
    reasons: list[str] = field(default_factory=list)
    breadth: dict[str, int] = field(default_factory=dict)
    leaders: list[Assessment] = field(default_factory=list)
    laggards: list[Assessment] = field(default_factory=list)


def market_view(benchmark: Metrics | None, assessments: list[Assessment],
                macro_hits: dict[str, list[NewsItem]] | None = None) -> MarketView:
    reasons: list[str] = []
    score = 0.0

    if benchmark is not None:
        for window in ("1d", "1w", "1m"):
            value = benchmark.ret.get(window)
            if value is not None:
                reasons.append(f"{benchmark.instrument.name}{WINDOW_LABELS[window]} {_fmt(value)}")
        month = benchmark.ret.get("1m")
        if month is not None:
            score += _clamp(month, -8, 8) * 0.5
        trend = classify_trend(benchmark)
        if trend == TREND_BULL:
            score += 2
            reasons.append("大盘处于多头排列")
        elif trend == TREND_BEAR:
            score -= 2
            reasons.append("大盘处于空头排列")
        if benchmark.range_position is not None:
            reasons.append(f"大盘位于近半年区间 {benchmark.range_position:.0f} 分位")
            if benchmark.range_position >= 90:
                score -= 1
            elif benchmark.range_position <= 20:
                score += 1

    cn = [a for a in assessments if a.metrics.instrument.market == "A股"]
    up = sum(1 for a in cn if (a.metrics.ret.get("1d") or 0) > 0)
    down = sum(1 for a in cn if (a.metrics.ret.get("1d") or 0) < 0)
    breadth = {"上涨": up, "下跌": down, "合计": len(cn)}
    if cn:
        ratio = up / len(cn)
        reasons.append(f"观察池内A股标的今日 {up} 涨 / {down} 跌")
        score += (ratio - 0.5) * 4

    if macro_hits:
        hot = sorted(macro_hits.items(), key=lambda kv: -len(kv[1]))[:2]
        reasons.append("今日主导消息类别：" + "、".join(f"{k}({len(v)}条)" for k, v in hot))

    if score >= 4:
        temperature, position = "偏热", "7–8成，以持有已盈利方向为主，新仓等回调"
    elif score >= 1.5:
        temperature, position = "温和偏暖", "6–7成，结构性加仓强势方向"
    elif score > -1.5:
        temperature, position = "中性震荡", "5–6成，哑铃配置（红利+强势成长），控制单一板块权重"
    elif score > -4:
        temperature, position = "偏冷", "3–5成，优先保留红利与低波资产"
    else:
        temperature, position = "明显偏冷", "2–4成，以防守为主，等趋势修复信号"

    ranked = [a for a in assessments if a.metrics.excess.get("1m") is not None]
    ranked.sort(key=lambda a: a.metrics.excess["1m"], reverse=True)
    return MarketView(temperature=temperature, suggested_position=position, reasons=reasons,
                      breadth=breadth, leaders=ranked[:5], laggards=ranked[-5:][::-1])
