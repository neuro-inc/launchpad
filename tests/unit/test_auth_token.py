from typing import Iterable

from starlette.requests import Request

from launchpad.auth.oauth import COOKIE_TOKEN, Oauth


def _make_request(headers: dict[str, str] | Iterable[tuple[str, str]] = {}) -> Request:
    # Build minimal ASGI scope for Request
    if isinstance(headers, dict):
        hdr_items = list(headers.items())
    else:
        hdr_items = list(headers)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(k.encode(), v.encode()) for k, v in hdr_items],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "scheme": "http",
        "root_path": "",
        "http_version": "1.1",
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


class DummyOauth(Oauth):
    def __init__(self, cookie_token: str | None = None) -> None:
        # do not call super().__init__ - we only need get_token_from_cookie
        self._cookie_token = cookie_token

    def get_token_from_cookie(self, request: Request) -> str | None:
        return request.cookies.get(COOKIE_TOKEN, self._cookie_token)


def test_token_from_request_prefers_cookie() -> None:
    from launchpad.auth.api import _token_from_request

    # set cookie header
    req = _make_request(headers={"cookie": f"{COOKIE_TOKEN}=cookie-123"})
    oauth = DummyOauth(cookie_token=None)
    token = _token_from_request(req, oauth, allow_cookie=True)
    assert token == "cookie-123"


def test_token_from_request_uses_authorization_header() -> None:
    from launchpad.auth.api import _token_from_request

    req = _make_request(headers={"authorization": "Bearer header-456"})
    oauth = DummyOauth(cookie_token=None)
    token = _token_from_request(req, oauth, allow_cookie=True)
    assert token == "header-456"


def test_token_from_request_cookie_disabled_uses_header() -> None:
    from launchpad.auth.api import _token_from_request

    req = _make_request(
        headers={
            "authorization": "Bearer hdr-789",
            "cookie": f"{COOKIE_TOKEN}=cookie-should-be-ignored",
        }
    )
    oauth = DummyOauth(cookie_token="cookie-should-be-ignored")
    token = _token_from_request(req, oauth, allow_cookie=False)
    assert token == "hdr-789"


def test_token_from_request_no_token_returns_none() -> None:
    from launchpad.auth.api import _token_from_request

    req = _make_request()
    oauth = DummyOauth(cookie_token=None)
    token = _token_from_request(req, oauth, allow_cookie=True)
    assert token is None
