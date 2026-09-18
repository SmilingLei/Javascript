import json

import pytest

from mdbrief.yuque import YuqueClient, YuqueError


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or json.dumps(payload or {}, ensure_ascii=False)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    """按 (method, path) 顺序返回预设响应，并记录收到的请求。"""

    def __init__(self, routes: dict):
        self.routes = routes
        self.calls: list[tuple[str, str, dict | None]] = []

    def request(self, method, url, headers=None, json=None, timeout=None):
        path = url.split("/api/v2", 1)[1]
        self.calls.append((method, path, json))
        assert headers and headers.get("X-Auth-Token") == "tk"
        assert headers.get("User-Agent")
        queue = self.routes.get((method, path))
        if queue is None:
            return FakeResponse(404, {"message": "Not Found"})
        return queue.pop(0) if isinstance(queue, list) else queue

    def paths(self, method=None):
        return [p for m, p, _ in self.calls if method is None or m == method]

    def payload_of(self, method, path):
        for m, p, body in self.calls:
            if m == method and p == path:
                return body
        return None


def client(session):
    return YuqueClient("tk", "me/market-brief", session=session)


def test_namespace_and_token_validation():
    with pytest.raises(YuqueError):
        YuqueClient("", "me/market-brief")
    with pytest.raises(YuqueError):
        YuqueClient("tk", "market-brief")


def test_publish_creates_doc_and_mounts_toc_when_absent():
    session = FakeSession({
        ("GET", "/repos/me/market-brief"): FakeResponse(200, {"data": {"id": 7}}),
        ("GET", "/repos/me/market-brief/docs/brief-2026-09-18-close"): FakeResponse(404, {}),
        ("POST", "/repos/me/market-brief/docs"): FakeResponse(
            200, {"data": {"id": 99, "slug": "brief-2026-09-18-close", "title": "市场简报 2026-09-18 16:40"}}),
        ("PUT", "/repos/me/market-brief/toc"): FakeResponse(200, {"data": []}),
    })
    result = client(session).publish(title="市场简报 2026-09-18 16:40",
                                    slug="brief-2026-09-18-close", body="# 报告")

    assert result.created is True
    assert result.doc_id == 99
    assert result.in_toc is True
    assert result.url == "https://www.yuque.com/me/market-brief/brief-2026-09-18-close"

    created = session.payload_of("POST", "/repos/me/market-brief/docs")
    assert created["format"] == "markdown"
    assert created["title"] == "市场简报 2026-09-18 16:40"
    assert created["body"] == "# 报告"
    assert session.payload_of("PUT", "/repos/me/market-brief/toc")["doc_ids"] == [99]


def test_publish_updates_existing_doc_instead_of_duplicating():
    session = FakeSession({
        ("GET", "/repos/me/market-brief"): FakeResponse(200, {"data": {"id": 7}}),
        ("GET", "/repos/me/market-brief/docs/brief-2026-09-18-close"): FakeResponse(
            200, {"data": {"id": 42, "slug": "brief-2026-09-18-close"}}),
        ("PUT", "/repos/me/market-brief/docs/42"): FakeResponse(
            200, {"data": {"id": 42, "slug": "brief-2026-09-18-close", "title": "新标题"}}),
    })
    result = client(session).publish(title="新标题", slug="brief-2026-09-18-close", body="正文")

    assert result.created is False
    assert result.doc_id == 42
    # 已存在的文档不再重复挂目录
    assert "/repos/me/market-brief/toc" not in session.paths("PUT")
    assert "/repos/me/market-brief/docs" not in session.paths("POST")


def test_publish_creates_repo_when_missing():
    session = FakeSession({
        ("GET", "/repos/me/market-brief"): FakeResponse(404, {}),
        ("POST", "/users/me/repos"): FakeResponse(200, {"data": {"id": 7, "slug": "market-brief"}}),
        ("GET", "/repos/me/market-brief/docs/brief-2026-09-18-close"): FakeResponse(404, {}),
        ("POST", "/repos/me/market-brief/docs"): FakeResponse(200, {"data": {"id": 1}}),
        ("PUT", "/repos/me/market-brief/toc"): FakeResponse(200, {"data": []}),
    })
    client(session).publish(title="t", slug="brief-2026-09-18-close", body="b")

    repo = session.payload_of("POST", "/users/me/repos")
    assert repo["slug"] == "market-brief"
    assert repo["public"] == 0


def test_toc_failure_falls_back_to_singular_doc_id_then_degrades():
    session = FakeSession({
        ("GET", "/repos/me/market-brief"): FakeResponse(200, {"data": {"id": 7}}),
        ("GET", "/repos/me/market-brief/docs/s"): FakeResponse(404, {}),
        ("POST", "/repos/me/market-brief/docs"): FakeResponse(200, {"data": {"id": 5}}),
        ("PUT", "/repos/me/market-brief/toc"): [
            FakeResponse(422, None, text="doc_ids invalid"),
            FakeResponse(200, {"data": []}),
        ],
    })
    result = client(session).publish(title="t", slug="s", body="b")
    assert result.in_toc is True
    assert session.payload_of("PUT", "/repos/me/market-brief/toc")["doc_ids"] == [5]

    session = FakeSession({
        ("GET", "/repos/me/market-brief"): FakeResponse(200, {"data": {"id": 7}}),
        ("GET", "/repos/me/market-brief/docs/s"): FakeResponse(404, {}),
        ("POST", "/repos/me/market-brief/docs"): FakeResponse(200, {"data": {"id": 5}}),
        ("PUT", "/repos/me/market-brief/toc"): [
            FakeResponse(422, None, text="bad"),
            FakeResponse(422, None, text="bad"),
        ],
    })
    # 目录挂载失败不应该让整次发布失败，文档本身已经写进去了
    result = client(session).publish(title="t", slug="s", body="b")
    assert result.created is True
    assert result.in_toc is False


def test_api_errors_are_surfaced():
    session = FakeSession({
        ("GET", "/repos/me/market-brief"): FakeResponse(200, {"data": {"id": 7}}),
        ("GET", "/repos/me/market-brief/docs/s"): FakeResponse(404, {}),
        ("POST", "/repos/me/market-brief/docs"): FakeResponse(401, None, text="Unauthorized"),
    })
    with pytest.raises(YuqueError, match="401"):
        client(session).publish(title="t", slug="s", body="b")


def test_publish_creates_repo_under_group_when_user_endpoint_rejects():
    session = FakeSession({
        ("GET", "/repos/team/market-brief"): FakeResponse(404, {}),
        ("POST", "/users/team/repos"): FakeResponse(403, None, text="Forbidden"),
        ("POST", "/groups/team/repos"): FakeResponse(200, {"data": {"id": 8}}),
        ("GET", "/repos/team/market-brief/docs/s"): FakeResponse(404, {}),
        ("POST", "/repos/team/market-brief/docs"): FakeResponse(200, {"data": {"id": 3}}),
        ("PUT", "/repos/team/market-brief/toc"): FakeResponse(200, {"data": []}),
    })
    result = YuqueClient("tk", "team/market-brief", session=session).publish(
        title="t", slug="s", body="b")

    assert result.doc_id == 3
    assert "/groups/team/repos" in session.paths("POST")


def test_publish_markdown_is_noop_without_credentials(monkeypatch):
    from mdbrief import yuque

    for var in ["YUQUE_TOKEN", "YUQUE_COOKIE", "YUQUE_NAMESPACE"]:
        monkeypatch.delenv(var, raising=False)
    assert yuque.publish_markdown("t", "s", "b") is None

    # 有 namespace 但没有任何凭据，同样不应该报错
    monkeypatch.setenv("YUQUE_NAMESPACE", "me/market-brief")
    assert yuque.publish_markdown("t", "s", "b") is None


class CookieSession(FakeSession):
    def request(self, method, url, headers=None, json=None, timeout=None):
        path = url.split("/api", 1)[1]
        self.calls.append((method, path, json))
        assert headers["X-CSRF-Token"] == "ct0k3n"
        assert headers["X-Requested-With"] == "XMLHttpRequest"
        assert "yuque_ctoken=ct0k3n" in headers["Cookie"]
        queue = self.routes.get((method, path))
        if queue is None:
            return FakeResponse(404, {"message": "Not Found"})
        return queue.pop(0) if isinstance(queue, list) else queue


COOKIE = "_yuque_session=abc; yuque_ctoken=ct0k3n"


def test_cookie_mode_requires_ctoken():
    from mdbrief.yuque import YuqueCookieClient

    with pytest.raises(YuqueError, match="yuque_ctoken"):
        YuqueCookieClient("_yuque_session=abc", "me/market-brief")


def test_cookie_mode_creates_doc_in_matching_book():
    from mdbrief.yuque import YuqueCookieClient

    session = CookieSession({
        ("GET", "/mine/books"): FakeResponse(200, {"data": [
            {"id": 11, "slug": "notes"}, {"id": 22, "slug": "market-brief"}]}),
        ("GET", "/docs/s?book_id=22&mode=markdown"): FakeResponse(404, {}),
        ("POST", "/docs"): FakeResponse(200, {"data": {"id": 55, "slug": "s"}}),
    })
    result = YuqueCookieClient(COOKIE, "me/market-brief", session=session).publish(
        title="市场简报 2026-09-18 16:40", slug="s", body="# 报告")

    assert result.created is True and result.doc_id == 55
    created = session.payload_of("POST", "/docs")
    assert created["book_id"] == 22
    assert created["format"] == "markdown"
    assert created["body"] == created["body_draft"] == "# 报告"


def test_cookie_mode_updates_then_publishes_existing_doc():
    from mdbrief.yuque import YuqueCookieClient

    session = CookieSession({
        ("GET", "/mine/books"): FakeResponse(200, {"data": [{"id": 22, "slug": "market-brief"}]}),
        ("GET", "/docs/s?book_id=22&mode=markdown"): FakeResponse(200, {"data": {"id": 55, "slug": "s"}}),
        ("PUT", "/docs/55/content"): FakeResponse(200, {"data": {}}),
        ("PUT", "/docs/55/publish"): FakeResponse(200, {"data": {}}),
    })
    result = YuqueCookieClient(COOKIE, "me/market-brief", session=session).publish(
        title="t", slug="s", body="正文")

    assert result.created is False
    # 网页端接口要先写草稿再发布，少一步内容不会真正更新
    assert session.paths("PUT") == ["/docs/55/content", "/docs/55/publish"]


def test_cookie_mode_reports_missing_book():
    from mdbrief.yuque import YuqueCookieClient

    session = CookieSession({
        ("GET", "/mine/books"): FakeResponse(200, {"data": [{"id": 11, "slug": "notes"}]}),
    })
    with pytest.raises(YuqueError, match="没找到"):
        YuqueCookieClient(COOKIE, "me/market-brief", session=session).publish(
            title="t", slug="s", body="b")


def test_check_credentials_reports_state(monkeypatch):
    from mdbrief import yuque

    for var in ["YUQUE_TOKEN", "YUQUE_COOKIE", "YUQUE_NAMESPACE"]:
        monkeypatch.delenv(var, raising=False)
    ready, detail = yuque.check_credentials()
    assert ready is False and "YUQUE_NAMESPACE" in detail

    monkeypatch.setenv("YUQUE_NAMESPACE", "me/market-brief")
    ready, detail = yuque.check_credentials()
    assert ready is False and "YUQUE_TOKEN" in detail
