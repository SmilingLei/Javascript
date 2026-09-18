"""命令行入口：python -m mdbrief [options]"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
from pathlib import Path

from . import envfile, llm, notify, report
from .config import PACKAGE_ROOT, load_config
from .pipeline import build_brief


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mdbrief",
        description="每日 A股板块ETF + 全球市场简报：抓行情与资讯，对比沪深300，给出操作建议",
    )
    p.add_argument("--config", default=None, help="配置目录，默认 config/")
    p.add_argument("--output-dir", default=str(PACKAGE_ROOT / "reports"), help="报告输出目录")
    p.add_argument("--no-news", action="store_true", help="跳过资讯抓取（只看行情）")
    p.add_argument("--fresh-hours", type=int, default=36, help="只保留最近多少小时的资讯")
    p.add_argument("--llm", action="store_true", help="调用 LLM 生成综述（需 LLM_API_KEY）")
    p.add_argument("--notify", action="store_true",
                   help="按环境变量推送到已配置渠道（语雀、微信、企微、飞书、Telegram、邮件）")
    p.add_argument("--yuque-slug", default=None,
                   help="指定语雀文档路径，默认 brief-{日期}-{场次}，同场次重跑会覆盖")
    p.add_argument("--json", dest="json_out", action="store_true", help="同时输出结构化 JSON")
    p.add_argument("--stdout", action="store_true", help="把 Markdown 打到标准输出")
    p.add_argument("--no-save", action="store_true", help="不写文件")
    p.add_argument("--check", action="store_true",
                   help="只自检推送渠道配置（会真的调一次语雀接口验证凭据），不生成报告")
    p.add_argument("--test-push", action="store_true",
                   help="只发一条测试消息到已配置渠道，不抓行情")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def _display_width(text: str) -> int:
    """中日韩字符在终端里占两列，用它做对齐。"""
    import unicodedata

    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _check_channels() -> int:
    rows = notify.check_channels()
    width = max(_display_width(name) for name, _, _ in rows)
    print("推送渠道自检：\n")
    for name, ready, detail in rows:
        padding = " " * (width - _display_width(name))
        print(f"  [{'OK' if ready else '--'}] {name}{padding}  {detail}")
    ready_names = [name for name, ready, _ in rows if ready]
    print()
    if ready_names:
        print("可用渠道：" + "、".join(ready_names))
        return 0
    print("没有任何渠道就绪，报告仍会写到 reports/，但不会推送。配置方法见 README「推送与归档」。")
    return 1


def _test_push() -> int:
    import datetime as dt

    from .pipeline import CST

    now = dt.datetime.now(CST)
    title = f"市场简报测试 {now:%Y-%m-%d %H:%M}"
    body = (
        "这是一条连通性测试。如果你在微信里看到这条消息，说明 SendKey 已经生效。\n\n"
        "正式日报会在每个交易日 16:20 和次日 06:30 自动推送。"
    )
    results = notify.notify_all(title, body, body, yuque_slug=None)
    sent = []
    for name, status in results.items():
        print(f"  {name}: {status}")
        if status.startswith("已"):
            sent.append(name)
    print()
    if sent:
        print("请打开微信（服务号「方糖」或你绑定的通道）确认是否收到：" + "、".join(sent))
        return 0
    print("没有渠道发送成功。先运行 `python -m mdbrief --check` 看缺什么。")
    return 1


def _to_jsonable(brief) -> dict:
    def conv(obj):
        if dataclasses.is_dataclass(obj):
            return {k: conv(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, dict):
            return {str(k): conv(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [conv(v) for v in obj]
        return obj

    return {
        "run_at": brief.run_at.isoformat(),
        "data_date": brief.data_date,
        "stale": brief.stale,
        "benchmark": conv(brief.benchmark),
        "view": conv(brief.view),
        "cn": conv(brief.cn_assessments),
        "global": conv(brief.global_assessments),
        "news": conv(brief.news.items),
        "errors": brief.errors,
        "llm_summary": brief.llm_summary,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("mdbrief")
    loaded = envfile.load_dotenv()
    if loaded:
        log.info("已加载本地密钥文件 %s", loaded.name)

    if args.check:
        return _check_channels()
    if args.test_push:
        return _test_push()

    config = load_config(args.config)
    log.info("观察列表 %d 个标的，资讯源 %d 个",
             len(config.instruments), sum(1 for s in config.news_sources if s.enabled))

    brief = build_brief(config, skip_news=args.no_news, fresh_hours=args.fresh_hours)
    if args.llm:
        brief.llm_summary = llm.summarize(brief)

    markdown = report.render_markdown(brief)
    digest = report.render_digest(brief)

    if not args.no_save:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = brief.data_date or f"{brief.run_at:%Y-%m-%d}"
        md_path = out_dir / f"{stamp}.md"
        md_path.write_text(markdown, encoding="utf-8")
        (out_dir / "latest.md").write_text(markdown, encoding="utf-8")
        log.info("已写入 %s", md_path)
        if args.json_out:
            json_path = out_dir / f"{stamp}.json"
            json_path.write_text(json.dumps(_to_jsonable(brief), ensure_ascii=False, indent=2),
                                 encoding="utf-8")
            log.info("已写入 %s", json_path)

    if args.stdout or args.no_save:
        sys.stdout.write(markdown)

    if args.notify:
        slug = args.yuque_slug or brief.doc_slug
        for channel, status in notify.notify_all(brief.title, digest, markdown,
                                                 yuque_slug=slug).items():
            log.info("推送 %s: %s", channel, status)

    if brief.errors:
        log.warning("本次有 %d 条数据告警", len(dict.fromkeys(brief.errors)))
    return 0
