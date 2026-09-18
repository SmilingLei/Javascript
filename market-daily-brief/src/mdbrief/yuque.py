"""把报告写入语雀知识库。

用的是语雀开放 API v2（认证头 `X-Auth-Token`）：
- `GET  /repos/{namespace}`                 知识库是否存在
- `POST /users/{login}/repos`               不存在时自动创建
- `GET  /repos/{namespace}/docs/{slug}`     同一 slug 是否已有文档
- `POST /repos/{namespace}/docs`            新建
- `PUT  /repos/{namespace}/docs/{id}`       已存在则覆盖（同一场次重跑不会刷出多篇）
- `PUT  /repos/{namespace}/toc`             把新文档挂进目录，否则只能在「未归档」里找到

Token 在 https://www.yuque.com/settings/tokens 生成。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.yuque.com/api/v2"
# 语雀会拦掉没有 User-Agent 的请求
USER_AGENT = "market-daily-brief/1.0 (+https://github.com/SmilingLei/Javascript)"
TIMEOUT = 30


class YuqueError(RuntimeError):
    pass


@dataclass
class PublishResult:
    doc_id: int
    slug: str
    title: str
    url: str
    created: bool
    in_toc: bool


class YuqueClient:
    def __init__(self, token: str, namespace: str, *, base_url: str = DEFAULT_BASE_URL,
                 session: requests.Session | None = None) -> None:
        if not token:
            raise YuqueError("缺少语雀 Token")
        if "/" not in namespace:
            raise YuqueError(f"namespace 应形如 login/repo-slug，当前为 {namespace!r}")
        self.token = token
        self.namespace = namespace.strip("/")
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    @property
    def login(self) -> str:
        return self.namespace.split("/", 1)[0]

    @property
    def repo_slug(self) -> str:
        return self.namespace.split("/", 1)[1]

    def _request(self, method: str, path: str, *, payload: dict | None = None,
                 allow_404: bool = False) -> dict | None:
        url = f"{self.base_url}{path}"
        resp = self.session.request(
            method, url,
            headers={"X-Auth-Token": self.token, "User-Agent": USER_AGENT,
                     "Content-Type": "application/json"},
            json=payload, timeout=TIMEOUT,
        )
        if allow_404 and resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise YuqueError(f"{method} {path} 返回 {resp.status_code}: {resp.text[:300]}")
        try:
            body = resp.json()
        except ValueError as exc:
            raise YuqueError(f"{method} {path} 返回的不是 JSON: {resp.text[:200]}") from exc
        return body.get("data") if isinstance(body, dict) else body

    def whoami(self) -> dict:
        return self._request("GET", "/user") or {}

    def ensure_repo(self, *, name: str | None = None, public: int = 0) -> dict:
        repo = self._request("GET", f"/repos/{self.namespace}", allow_404=True)
        if repo:
            return repo
        log.info("语雀知识库 %s 不存在，自动创建", self.namespace)
        return self._request("POST", f"/users/{self.login}/repos", payload={
            "name": name or "市场简报", "slug": self.repo_slug, "public": public,
            "description": "由 market-daily-brief 自动生成的每日市场简报",
        }) or {}

    def find_doc(self, slug: str) -> dict | None:
        return self._request("GET", f"/repos/{self.namespace}/docs/{slug}", allow_404=True)

    def add_to_toc(self, doc_id: int) -> bool:
        """把文档挂到目录根节点。失败不算致命错误，文档本身已经写进去了。"""
        payload = {"action": "appendNode", "action_mode": "child", "type": "DOC",
                   "doc_ids": [doc_id]}
        try:
            self._request("PUT", f"/repos/{self.namespace}/toc", payload=payload)
            return True
        except YuqueError as exc:
            log.warning("挂载目录失败（文档已创建）: %s", exc)
            # 老版本接口只认单数形式的 doc_id
            try:
                self._request("PUT", f"/repos/{self.namespace}/toc", payload={
                    "action": "appendNode", "action_mode": "child", "type": "DOC",
                    "doc_id": doc_id})
                return True
            except YuqueError as exc2:
                log.warning("挂载目录重试仍失败: %s", exc2)
                return False

    def publish(self, *, title: str, slug: str, body: str, public: int = 0,
                create_repo: bool = True) -> PublishResult:
        if create_repo:
            self.ensure_repo(public=public)

        existing = self.find_doc(slug)
        if existing:
            doc = self._request("PUT", f"/repos/{self.namespace}/docs/{existing['id']}", payload={
                "title": title, "slug": slug, "format": "markdown", "body": body,
                "public": public,
            }) or existing
            created = False
        else:
            doc = self._request("POST", f"/repos/{self.namespace}/docs", payload={
                "title": title, "slug": slug, "format": "markdown", "body": body,
                "public": public,
            }) or {}
            created = True

        doc_id = int(doc.get("id") or (existing or {}).get("id") or 0)
        in_toc = self.add_to_toc(doc_id) if (created and doc_id) else True
        return PublishResult(
            doc_id=doc_id,
            slug=doc.get("slug") or slug,
            title=doc.get("title") or title,
            url=f"https://www.yuque.com/{self.namespace}/{doc.get('slug') or slug}",
            created=created,
            in_toc=in_toc,
        )


def publish_markdown(title: str, slug: str, body: str) -> PublishResult | None:
    """按环境变量发布；未配置 Token/namespace 时返回 None。"""
    token = os.getenv("YUQUE_TOKEN")
    namespace = os.getenv("YUQUE_NAMESPACE")
    if not token or not namespace:
        return None

    client = YuqueClient(token, namespace, base_url=os.getenv("YUQUE_BASE_URL", DEFAULT_BASE_URL))
    return client.publish(
        title=title, slug=slug, body=body,
        public=int(os.getenv("YUQUE_PUBLIC", "0")),
        create_repo=os.getenv("YUQUE_CREATE_REPO", "1") != "0",
    )
