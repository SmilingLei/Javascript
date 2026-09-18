"""推送：Server酱、企业微信、飞书、Telegram、邮件。按环境变量自动启用。"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

import requests

log = logging.getLogger(__name__)

TIMEOUT = 20


def _post(url: str, **kwargs) -> None:
    resp = requests.post(url, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()


def push_serverchan(title: str, content: str) -> bool:
    key = os.getenv("SERVERCHAN_SENDKEY")
    if not key:
        return False
    _post(f"https://sctapi.ftqq.com/{key}.send", data={"title": title[:100], "desp": content})
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
    "企业微信": push_wecom,
    "飞书": push_feishu,
    "Telegram": push_telegram,
    "邮件": push_email,
}


def notify_all(title: str, short: str, full: str) -> dict[str, str]:
    """返回 {渠道: 状态}。短文本用于 IM，邮件用完整 Markdown。"""
    results: dict[str, str] = {}
    for name, sender in CHANNELS.items():
        payload = full if name == "邮件" else short
        try:
            results[name] = "已发送" if sender(title, payload) else "未配置"
        except Exception as exc:  # noqa: BLE001
            log.warning("%s 推送失败: %s", name, exc)
            results[name] = f"失败: {exc}"
    return results
