"""带重试与超时的 HTTP 会话，所有数据源共用。"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class Http:
    def __init__(self, timeout: int = 15, retries: int = 3, backoff: float = 1.5) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})

    def get(self, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None,
            encoding: str | None = None) -> requests.Response:
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
                resp.raise_for_status()
                if encoding:
                    resp.encoding = encoding
                return resp
            except Exception as exc:  # noqa: BLE001 - 数据源千奇百怪，统一重试
                last = exc
                if attempt < self.retries - 1:
                    time.sleep(self.backoff ** attempt)
        assert last is not None
        raise last

    def get_json(self, url: str, **kwargs: Any) -> Any:
        resp = self.get(url, **kwargs)
        if kwargs.get("encoding"):
            # 有些接口不声明 charset，requests 的自动探测会把中文解成乱码
            import json

            return json.loads(resp.text)
        return resp.json()

    def get_text(self, url: str, **kwargs: Any) -> str:
        return self.get(url, **kwargs).text

    def close(self) -> None:
        self.session.close()
