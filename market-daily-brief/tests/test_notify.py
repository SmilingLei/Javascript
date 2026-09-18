import datetime as dt
import os

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


ALL_VARS = ["SERVERCHAN_SENDKEY", "PUSHPLUS_TOKEN", "WECOM_WEBHOOK", "FEISHU_WEBHOOK",
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SMTP_HOST", "SMTP_PORT", "MAIL_TO",
            "SMTP_USER", "SMTP_PASSWORD", "YUQUE_TOKEN", "YUQUE_COOKIE", "YUQUE_NAMESPACE"]


def test_notify_all_reports_unconfigured_channels(monkeypatch):
    for var in ALL_VARS:
        monkeypatch.delenv(var, raising=False)

    results = notify.notify_all("市场简报 2026-09-18 16:40", "摘要", "# 全文", yuque_slug="brief-x")
    assert results["语雀"] == "未配置"
    assert results["Server酱"] == "未配置"
    assert set(results) == {"语雀", "Server酱", "PushPlus", "企业微信", "飞书", "Telegram", "邮件"}


def test_serverchan_ok_reads_business_code_not_http_status():
    ok, detail = notify._serverchan_ok({"code": 0, "data": {"pushid": "123"}})
    assert ok is True and "123" in detail
    ok, detail = notify._serverchan_ok({"code": 40001, "message": "bad pushtoken"})
    assert ok is False and "bad pushtoken" in detail


def test_load_dotenv_does_not_override_existing_env(tmp_path, monkeypatch):
    from mdbrief.envfile import load_dotenv

    env = tmp_path / ".env"
    env.write_text("SERVERCHAN_SENDKEY=from-file\nOTHER=abc\n", encoding="utf-8")
    monkeypatch.setenv("SERVERCHAN_SENDKEY", "already-set")
    monkeypatch.delenv("OTHER", raising=False)
    assert load_dotenv(env) == env
    assert os.environ["SERVERCHAN_SENDKEY"] == "already-set"
    assert os.environ["OTHER"] == "abc"
    # Turbo 的 key 以 SCT 开头，推微信
    assert notify.serverchan_endpoint("SCT12345xyz") == "https://sctapi.ftqq.com/SCT12345xyz.send"
    # Server酱³ 的 key 形如 sctp{uid}t...，域名里要带 uid
    assert notify.serverchan_endpoint("sctp123tABC") == "https://123.push.ft07.com/send/sctp123tABC.send"


def test_check_channels_lists_missing_variables(monkeypatch):
    for var in ALL_VARS:
        monkeypatch.delenv(var, raising=False)
    rows = dict((name, (ready, detail)) for name, ready, detail in notify.check_channels())

    assert rows["Server酱"][0] is False
    assert "SERVERCHAN_SENDKEY" in rows["Server酱"][1]
    assert rows["语雀"][0] is False
    assert "YUQUE_NAMESPACE" in rows["语雀"][1]
    assert "TELEGRAM_CHAT_ID" in rows["Telegram"][1]


def test_check_channels_marks_configured(monkeypatch):
    for var in ALL_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SERVERCHAN_SENDKEY", "SCTxxx")
    monkeypatch.setattr(notify.yuque, "check_credentials", lambda: (True, "Token 有效（账号 me）"))

    rows = dict((name, (ready, detail)) for name, ready, detail in notify.check_channels())
    assert rows["Server酱"][0] is True
    assert rows["语雀"] == (True, "Token 有效（账号 me）")
    assert rows["PushPlus"][0] is False


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
