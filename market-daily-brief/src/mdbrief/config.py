"""配置加载与校验。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .models import Instrument

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PACKAGE_ROOT / "config"


@dataclass
class Benchmark:
    key: str
    symbol: str
    name: str
    provider: str = "tencent"

    def as_instrument(self) -> Instrument:
        return Instrument(
            symbol=self.symbol,
            name=self.name,
            provider=self.provider,
            group="基准",
            market="基准",
            kind="指数",
        )


@dataclass
class NewsSource:
    id: str
    name: str
    enabled: bool = True
    limit: int = 20
    region: str = "国内"
    weight: int = 1
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    benchmarks: dict[str, Benchmark]
    instruments: list[Instrument]
    news_sources: list[NewsSource]
    macro_keywords: dict[str, list[str]]
    sentiment: dict[str, list[str]]
    cross_reference_benchmark: str | None = None

    def benchmark(self, key: str | None) -> Benchmark | None:
        if not key:
            return None
        return self.benchmarks.get(key)

    @property
    def cross_reference(self) -> Benchmark | None:
        return self.benchmark(self.cross_reference_benchmark)

    def benchmark_instruments(self) -> list[Instrument]:
        return [b.as_instrument() for b in self.benchmarks.values()]


_INSTRUMENT_FIELDS = {"symbol", "name", "provider", "group", "market", "kind", "benchmark",
                      "history_symbol", "keywords", "note"}


def _build_instrument(raw: dict[str, Any], group: dict[str, Any]) -> Instrument:
    unknown = set(raw) - _INSTRUMENT_FIELDS
    if unknown:
        raise ValueError(f"标的 {raw.get('symbol')} 含未知字段: {sorted(unknown)}")
    data = {
        "group": group.get("name", "其他"),
        "market": group.get("market", "A股"),
        "provider": group.get("provider", "tencent"),
        "benchmark": group.get("benchmark"),
        "kind": group.get("kind", "ETF"),
    }
    data.update(raw)
    return Instrument(
        symbol=str(data["symbol"]),
        name=str(data["name"]),
        provider=str(data["provider"]),
        group=str(data["group"]),
        market=str(data["market"]),
        kind=str(data.get("kind") or "ETF"),
        benchmark=data.get("benchmark"),
        history_symbol=data.get("history_symbol"),
        keywords=list(data.get("keywords") or []),
        note=data.get("note"),
    )


def load_config(config_dir: str | Path | None = None) -> Config:
    directory = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    watchlist = yaml.safe_load((directory / "watchlist.yml").read_text(encoding="utf-8")) or {}
    news_cfg = yaml.safe_load((directory / "news.yml").read_text(encoding="utf-8")) or {}

    benchmarks: dict[str, Benchmark] = {}
    for key, raw in (watchlist.get("benchmarks") or {}).items():
        benchmarks[key] = Benchmark(key=key, symbol=str(raw["symbol"]), name=str(raw["name"]),
                                    provider=str(raw.get("provider", "tencent")))

    instruments: list[Instrument] = []
    seen: set[str] = set()
    for group in watchlist.get("groups") or []:
        for raw in group.get("instruments") or []:
            inst = _build_instrument(dict(raw), group)
            if inst.benchmark and inst.benchmark not in benchmarks:
                raise ValueError(f"标的 {inst.symbol} 引用了不存在的基准 {inst.benchmark}")
            if inst.symbol in seen:
                raise ValueError(f"标的重复: {inst.symbol}")
            seen.add(inst.symbol)
            instruments.append(inst)

    sources: list[NewsSource] = []
    for raw in news_cfg.get("sources") or []:
        raw = dict(raw)
        source = NewsSource(
            id=str(raw.pop("id")),
            name=str(raw.pop("name", raw.get("id", "news"))),
            enabled=bool(raw.pop("enabled", True)),
            limit=int(raw.pop("limit", 20)),
            region=str(raw.pop("region", "国内")),
            weight=int(raw.pop("weight", 1)),
        )
        source.options = raw
        sources.append(source)

    return Config(
        benchmarks=benchmarks,
        instruments=instruments,
        news_sources=sources,
        macro_keywords={k: list(v) for k, v in (news_cfg.get("macro_keywords") or {}).items()},
        sentiment={k: list(v) for k, v in (news_cfg.get("sentiment") or {}).items()},
        cross_reference_benchmark=watchlist.get("cross_reference_benchmark"),
    )
