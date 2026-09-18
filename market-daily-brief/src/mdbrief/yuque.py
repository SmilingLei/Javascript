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
# 网页端内部接口，Cookie 模式用
WEB_API_URL = "https://www.yuque.com/api"
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
        payload = {"name": name or "市场简报", "slug": self.repo_slug, "public": public,
                   "description": "由 market-daily-brief 自动生成的每日市场简报"}
        try:
            return self._request("POST", f"/users/{self.login}/repos", payload=payload) or {}
        except YuqueError as exc:
            # namespace 第一段也可能是团队 login，这时要建到团队下
            log.info("按个人空间创建失败（%s），改按团队空间创建", exc)
            return self._request("POST", f"/groups/{self.login}/repos", payload=payload) or {}

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


class YuqueCookieClient:
    """Cookie 模式：走语雀网页端内部接口，不需要超级会员。

    这是社区方案（elog 等工具同路线），**用的不是公开 API**：语雀改版可能失效，
    而且浏览器 Cookie 大约两周过期，需要重新粘贴。只在没有超级会员时作为兜底。
    """

    def __init__(self, cookie: str, namespace: str, *, base_url: str = WEB_API_URL,
                 session: requests.Session | None = None) -> None:
        if not cookie:
            raise YuqueError("缺少语雀 Cookie")
        if "/" not in namespace:
            raise YuqueError(f"namespace 应形如 login/repo-slug，当前为 {namespace!r}")
        self.cookie = cookie.strip()
        self.namespace = namespace.strip("/")
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.ctoken = self._extract_ctoken(self.cookie)
        if not self.ctoken:
            raise YuqueError("Cookie 里没有 yuque_ctoken，写操作会被 CSRF 拦截，请复制完整的 Cookie")

    @staticmethod
    def _extract_ctoken(cookie: str) -> str:
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "yuque_ctoken":
                return value.strip()
        return ""

    @property
    def login(self) -> str:
        return self.namespace.split("/", 1)[0]

    @property
    def repo_slug(self) -> str:
        return self.namespace.split("/", 1)[1]

    def _request(self, method: str, path: str, *, payload: dict | None = None,
                 allow_404: bool = False) -> dict | list | None:
        resp = self.session.request(
            method, f"{self.base_url}{path}",
            headers={
                "Cookie": self.cookie,
                "X-CSRF-Token": self.ctoken,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"https://www.yuque.com/{self.namespace}",
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
            },
            json=payload, timeout=TIMEOUT,
        )
        if allow_404 and resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise YuqueError(f"{method} {path} 返回 {resp.status_code}: {resp.text[:300]}"
                             "（Cookie 可能已过期，请重新复制）")
        try:
            body = resp.json()
        except ValueError as exc:
            raise YuqueError(f"{method} {path} 返回的不是 JSON，Cookie 可能已失效") from exc
        return body.get("data") if isinstance(body, dict) else body

    def book_id(self) -> int:
        books = self._request("GET", "/mine/books") or []
        for book in books if isinstance(books, list) else []:
            if book.get("slug") == self.repo_slug:
                return int(book["id"])
        raise YuqueError(f"在你的知识库列表里没找到 slug 为 {self.repo_slug} 的知识库，"
                         "Cookie 模式不会自动建库，请先在语雀网页上手动创建")

    def publish(self, *, title: str, slug: str, body: str, public: int = 0) -> PublishResult:
        book = self.book_id()
        existing = self._request("GET", f"/docs/{slug}?book_id={book}&mode=markdown",
                                 allow_404=True)
        if existing and existing.get("id"):
            doc_id = int(existing["id"])
            self._request("PUT", f"/docs/{doc_id}/content",
                          payload={"body": body, "body_draft": body, "format": "markdown",
                                   "title": title})
            self._request("PUT", f"/docs/{doc_id}/publish", payload={"body": body})
            created = False
            doc_slug = existing.get("slug") or slug
        else:
            doc = self._request("POST", "/docs", payload={
                "book_id": book, "title": title, "slug": slug, "format": "markdown",
                "body": body, "body_draft": body, "public": public,
            }) or {}
            doc_id = int(doc.get("id") or 0)
            created = True
            doc_slug = doc.get("slug") or slug

        return PublishResult(doc_id=doc_id, slug=doc_slug, title=title,
                             url=f"https://www.yuque.com/{self.namespace}/{doc_slug}",
                             created=created, in_toc=True)


def check_credentials() -> tuple[bool, str]:
    """验证语雀凭据是否可用，返回 (是否就绪, 人类可读的说明)。"""
    namespace = os.getenv("YUQUE_NAMESPACE")
    token = os.getenv("YUQUE_TOKEN")
    cookie = os.getenv("YUQUE_COOKIE")

    if not namespace:
        return False, "未设置 YUQUE_NAMESPACE（形如 你的语雀用户名/market-brief）"
    if not token and not cookie:
        return False, "未设置 YUQUE_TOKEN，也未设置 YUQUE_COOKIE"

    try:
        if token:
            client = YuqueClient(token, namespace,
                                 base_url=os.getenv("YUQUE_BASE_URL", DEFAULT_BASE_URL))
            user = client.whoami()
            who = user.get("login") or user.get("name") or "未知账号"
            repo = client._request("GET", f"/repos/{namespace}", allow_404=True)
            state = "知识库已存在" if repo else "知识库不存在，首次运行会自动创建"
            return True, f"Token 有效（账号 {who}），{state}"

        client = YuqueCookieClient(cookie, namespace,
                                   base_url=os.getenv("YUQUE_WEB_API_URL", WEB_API_URL))
        return True, f"Cookie 有效，知识库 id={client.book_id()}（Cookie 模式，约两周需重新获取）"
    except YuqueError as exc:
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001
        return False, f"校验时出错: {exc}"


def publish_markdown(title: str, slug: str, body: str) -> PublishResult | None:
    """按环境变量发布；未配置凭据时返回 None。Token 优先，其次 Cookie。"""
    namespace = os.getenv("YUQUE_NAMESPACE")
    token = os.getenv("YUQUE_TOKEN")
    cookie = os.getenv("YUQUE_COOKIE")
    if not namespace or not (token or cookie):
        return None

    public = int(os.getenv("YUQUE_PUBLIC", "0"))
    if token:
        client = YuqueClient(token, namespace,
                             base_url=os.getenv("YUQUE_BASE_URL", DEFAULT_BASE_URL))
        return client.publish(title=title, slug=slug, body=body, public=public,
                              create_repo=os.getenv("YUQUE_CREATE_REPO", "1") != "0")

    log.info("未设置 YUQUE_TOKEN，改用 Cookie 模式（网页端接口，非公开 API）")
    return YuqueCookieClient(cookie, namespace,
                             base_url=os.getenv("YUQUE_WEB_API_URL", WEB_API_URL)).publish(
        title=title, slug=slug, body=body, public=public)
