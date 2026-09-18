"""可选的 LLM 综述。未配置 API Key 时整份报告仍然可用（规则引擎已给出结论）。

支持任何 OpenAI 兼容接口：DeepSeek、通义、Kimi、OpenAI、本地 vLLM 等。
环境变量：LLM_API_KEY（必填）、LLM_BASE_URL、LLM_MODEL。
"""

from __future__ import annotations

import json
import logging
import os

from .http import Http
from .pipeline import Brief

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"

SYSTEM_PROMPT = (
    "你是一位严谨的A股与全球市场策略分析师。基于给定的结构化数据（已经算好的涨跌幅、"
    "相对沪深300的超额、趋势状态、资讯标题）写一份中文日报综述。要求："
    "1) 先给3条最重要的结论；2) 说明A股内部哪些板块在领跑/落后，以及可能的驱动原因；"
    "3) 结合海外市场与大类资产给出对A股的影响判断；4) 给出明确的操作倾向（加仓/持有/减仓/观望）"
    "并解释原因和触发条件；5) 指出2条主要风险。不要编造数据里没有的数字，不确定就说不确定。"
    "总字数控制在600字以内，用小标题和短句。"
)


def _facts(brief: Brief) -> dict:
    def entry(a) -> dict:
        m = a.metrics
        return {
            "名称": m.instrument.name,
            "市场": m.instrument.market,
            "分组": m.instrument.group,
            "今日": m.ret.get("1d"),
            "近1周": m.ret.get("1w"),
            "近1月": m.ret.get("1m"),
            "近3月": m.ret.get("3m"),
            "近1周超额": m.excess.get("1w"),
            "近1月超额": m.excess.get("1m"),
            "区间位置分位": m.range_position,
            "趋势": a.trend,
            "规则建议": a.action,
            "评分": a.score,
        }

    view = brief.view
    return {
        "日期": f"{brief.run_at:%Y-%m-%d}",
        "行情日期": brief.data_date,
        "基准": {
            "名称": brief.benchmark.instrument.name if brief.benchmark else None,
            "今日": brief.benchmark.ret.get("1d") if brief.benchmark else None,
            "近1周": brief.benchmark.ret.get("1w") if brief.benchmark else None,
            "近1月": brief.benchmark.ret.get("1m") if brief.benchmark else None,
            "区间位置分位": brief.benchmark.range_position if brief.benchmark else None,
        },
        "市场温度": view.temperature if view else None,
        "规则仓位建议": view.suggested_position if view else None,
        "A股板块": [entry(a) for a in brief.cn_assessments],
        "全球市场": [entry(a) for a in brief.global_assessments],
        "重要资讯": [
            {"来源": i.source, "标题": i.title, "标签": i.tags[:4], "地区": i.region}
            for i in brief.news.top(35)
        ],
    }


def summarize(brief: Brief, *, http: Http | None = None) -> str | None:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        log.info("未设置 LLM_API_KEY，跳过 AI 综述")
        return None

    base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL)
    own = http is None
    http = http or Http(timeout=120, retries=2)
    try:
        resp = http.session.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(_facts(brief), ensure_ascii=False)},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        return (resp.json()["choices"][0]["message"]["content"] or "").strip() or None
    except Exception as exc:  # noqa: BLE001 - AI 是增强项，失败不影响报告
        log.warning("AI 综述失败: %s", exc)
        brief.errors.append(f"AI 综述失败: {exc}")
        return None
    finally:
        if own:
            http.close()
