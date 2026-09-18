"""推送：语雀、Server酱（微信）、企业微信、飞书、Telegram、邮件。按环境变量自动启用。"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

import requests

from . import yuque

log = logging.getLogger(__name__)

TIMEOUT = 20


def _post(url: str, **kwargs) -> requests.Response:
    resp = requests.post(url, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp


def _serverchan_ok(payload: object) -> tuple[bool, str]:
    """Server酱 即使失败也经常返回 HTTP 200，必须看 JSON 里的 code/errno。"""
    if not isinstance(payload, dict):
        return True, "已发送"
    code = payload.get("code", payload.get("errno"))
    if code in (0, None, "0"):
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        pushid = data.get("pushid")
        return True, f"已发送（pushid={pushid}）" if pushid else "已发送"
    message = payload.get("message") or payload.get("msg") or str(payload)
    return False, f"接口拒绝: {message}"


def serverchan_endpoint(key: str) -> str:
    """Server酱有两条产品线，SendKey 前缀不同，接口域名也不同。

    - Turbo（`SCT` 开头）推微信：https://sctapi.ftqq.com/<key>.send
    - Server酱³（`sctp{uid}t...` 开头）推自有 App：https://<uid>.push.ft07.com/send/<key>.send
    """
    if key.startswith("sctp"):
        uid = "".join(ch for ch in key[4:].split("t", 1)[0] if ch.isdigit())
        if uid:
            return f"https://{uid}.push.ft07.com/send/{key}.send"
    return f"https://sctapi.ftqq.com/{key}.send"


def push_serverchan(title: str, content: str) -> bool:
    key = os.getenv("SERVERCHAN_SENDKEY")
    if not key:
        return False
    resp = _post(serverchan_endpoint(key), data={"title": title[:100], "desp": content})
    try:
        payload = resp.json()
    except ValueError:
        return True
    ok, detail = _serverchan_ok(payload)
    if not ok:
        raise RuntimeError(detail)
    log.info("Server酱 %s", detail)
    return True


def push_pushplus(title: str, content: str) -> bool:
    """PushPlus：微信推送的另一个免费选择，额度比 Server酱 免费版宽松。"""
    token = os.getenv("PUSHPLUS_TOKEN")
    if not token:
        return False
    _post("https://www.pushplus.plus/send",
          json={"token": token, "title": title[:100], "content": content, "template": "markdown"})
    return True


def push_wecom(title: str, content: str) -> bool:
    url = os.getenv("WECOM_WEBHOOK")
    if not url:
        return False
    # 企业微信 markdown 上限 4096 字节
    body = f"## {title}\n{content}"[:4000]
    _post(url, json={"msgtype": "markdown", "markdown": {"content": body}})
    return True


def push_feishu(title: str, content: str) -> bool:
    url = os.getenv("FEISHU_WEBHOOK")
    if not url:
        return False
    _post(url, json={"msg_type": "text", "content": {"text": f"{title}\n{content}"[:9000]}})
    return True


def push_telegram(title: str, content: str) -> bool:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    _post(f"https://api.telegram.org/bot{token}/sendMessage",
          json={"chat_id": chat, "text": f"{title}\n\n{content}"[:4000],
                "disable_web_page_preview": True})
    return True


def push_email(title: str, content: str) -> bool:
    host = os.getenv("SMTP_HOST")
    to_addr = os.getenv("MAIL_TO")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not all([host, to_addr, user, password]):
        return False

    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = os.getenv("MAIL_FROM", user)
    msg["To"] = to_addr
    msg.set_content(content)

    port = int(os.getenv("SMTP_PORT", "465"))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
    return True


CHANNELS = {
    "Server酱": push_serverchan,
    "PushPlus": push_pushplus,
    "企业微信": push_wecom,
    "飞书": push_feishu,
    "Telegram": push_telegram,
    "邮件": push_email,
}

# 邮件和语雀收完整 Markdown，IM 收精简摘要
FULL_TEXT_CHANNELS = {"邮件", "语雀"}


def publish_yuque(title: str, content: str, slug: str) -> str | None:
    """写入语雀文档，返回文档链接；未配置则返回 None。"""
    result = yuque.publish_markdown(title, slug, content)
    if result is None:
        return None
    if not result.in_toc:
        log.warning("语雀文档已写入但未挂进目录，可在知识库「未归档」中找到：%s", result.url)
    return result.url


CHANNEL_ENV_HINTS = {
    "语雀": ("YUQUE_NAMESPACE + YUQUE_TOKEN（超级会员）或 YUQUE_COOKIE（免费）", ("YUQUE_NAMESPACE",)),
    "Server酱": ("SERVERCHAN_SENDKEY", ("SERVERCHAN_SENDKEY",)),
    "PushPlus": ("PUSHPLUS_TOKEN", ("PUSHPLUS_TOKEN",)),
    "企业微信": ("WECOM_WEBHOOK", ("WECOM_WEBHOOK",)),
    "飞书": ("FEISHU_WEBHOOK", ("FEISHU_WEBHOOK",)),
    "Telegram": ("TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID", ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")),
    "邮件": ("SMTP_HOST + SMTP_USER + SMTP_PASSWORD + MAIL_TO",
             ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_TO")),
}


def check_channels() -> list[tuple[str, bool, str]]:
    """自检各渠道配置，返回 [(渠道, 是否就绪, 说明)]。语雀会真的调一次接口验证。"""
    rows: list[tuple[str, bool, str]] = []
    for channel, (hint, required) in CHANNEL_ENV_HINTS.items():
        if channel == "语雀":
            ready, detail = yuque.check_credentials()
            rows.append((channel, ready, detail if ready else f"{detail}；需要 {hint}"))
            continue
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            rows.append((channel, False, f"未配置，缺 {'、'.join(missing)}"))
        else:
            rows.append((channel, True, f"已配置（{hint}）"))
    return rows


def notify_all(title: str, short: str, full: str, *, yuque_slug: str | None = None) -> dict[str, str]:
    """返回 {渠道: 状态}。语雀和邮件收完整报告，IM 收摘要。"""
    results: dict[str, str] = {}

    if yuque_slug:
        try:
            url = publish_yuque(title, full, yuque_slug)
            results["语雀"] = f"已写入 {url}" if url else "未配置"
        except Exception as exc:  # noqa: BLE001
            log.warning("语雀写入失败: %s", exc)
            results["语雀"] = f"失败: {exc}"

    for name, sender in CHANNELS.items():
        payload = full if name in FULL_TEXT_CHANNELS else short
        try:
            results[name] = "已发送" if sender(title, payload) else "未配置"
        except Exception as exc:  # noqa: BLE001
            log.warning("%s 推送失败: %s", name, exc)
            results[name] = f"失败: {exc}"
    return results
