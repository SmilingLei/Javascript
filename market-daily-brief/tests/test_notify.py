import datetime as dt

from mdbrief import notify
from mdbrief.pipeline import CST, Brief


def make_brief(hour: int, minute: int = 40) -> Brief:
    return Brief(run_at=dt.datetime(2026, 9, 18, hour, minute, tzinfo=CST), benchmark=None)


def test_title_carries_date_and_time():
    assert make_brief(16).title == "市场简报 2026-09-18 16:40"
    assert make_brief(6, 30).title == "市场简报 2026-09-18 06:30"


def test_slug_separates_close_and_overnight_sessions():
    assert make_brief(16).doc_slug == "brief-2026-09-18-close"
    assert make_brief(6, 30).doc_slug == "brief-2026-09-18-overnight"


def test_notify_all_reports_unconfigured_channels(monkeypatch):
    for var in ["SERVERCHAN_SENDKEY", "WECOM_WEBHOOK", "FEISHU_WEBHOOK", "TELEGRAM_BOT_TOKEN",
                "TELEGRAM_CHAT_ID", "SMTP_HOST", "MAIL_TO", "SMTP_USER", "SMTP_PASSWORD",
                "YUQUE_TOKEN", "YUQUE_NAMESPACE"]:
        monkeypatch.delenv(var, raising=False)

    results = notify.notify_all("市场简报 2026-09-18 16:40", "摘要", "# 全文", yuque_slug="brief-x")
    assert results["语雀"] == "未配置"
    assert results["Server酱"] == "未配置"
    assert set(results) == {"语雀", "Server酱", "企业微信", "飞书", "Telegram", "邮件"}


def test_wechat_gets_digest_and_yuque_gets_full_markdown(monkeypatch):
    sent: dict[str, str] = {}

    def fake_serverchan(title, content):
        sent["wechat_title"] = title
        sent["wechat_body"] = content
        return True

    def fake_yuque(title, slug, body):
        sent["yuque_title"] = title
        sent["yuque_slug"] = slug
        sent["yuque_body"] = body

        class R:
            url = "https://www.yuque.com/me/market-brief/brief-x"
            in_toc = True

        return R()

    monkeypatch.setitem(notify.CHANNELS, "Server酱", fake_serverchan)
    monkeypatch.setattr(notify.yuque, "publish_markdown", fake_yuque)
    for var in ["WECOM_WEBHOOK", "FEISHU_WEBHOOK", "TELEGRAM_BOT_TOKEN", "SMTP_HOST"]:
        monkeypatch.delenv(var, raising=False)

    results = notify.notify_all("市场简报 2026-09-18 16:40", "摘要正文", "# 完整报告",
                                yuque_slug="brief-x")

    assert results["Server酱"] == "已发送"
    assert results["语雀"].startswith("已写入 https://www.yuque.com/")
    assert sent["wechat_title"] == sent["yuque_title"] == "市场简报 2026-09-18 16:40"
    assert sent["wechat_body"] == "摘要正文"
    assert sent["yuque_body"] == "# 完整报告"
    assert sent["yuque_slug"] == "brief-x"


def test_yuque_failure_does_not_block_wechat(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("token 过期")

    monkeypatch.setattr(notify.yuque, "publish_markdown", boom)
    monkeypatch.setitem(notify.CHANNELS, "Server酱", lambda *a: True)
    results = notify.notify_all("t", "s", "f", yuque_slug="brief-x")

    assert results["语雀"].startswith("失败")
    assert results["Server酱"] == "已发送"
