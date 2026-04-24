from __future__ import annotations

from typing import Callable, Iterable, Optional

import pytest
from starlette.requests import Request

from launchpad.auth.api import _token_from_request
from launchpad.auth.oauth import COOKIE_TOKEN, Oauth


def _normalize_headers(
    headers: Optional[dict[str, str] | Iterable[tuple[str, str]]],
) -> list[tuple[bytes, bytes]]:
    if headers is None:
        return []

    items_iter: Iterable[tuple[str, str]] = (
        headers.items() if isinstance(headers, dict) else headers
    )

    return [(k.lower().encode(), v.encode()) for k, v in items_iter]


def _build_request(
    headers: Optional[dict[str, str] | Iterable[tuple[str, str]]] = None,
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": _normalize_headers(headers),
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
    """Test double with explicit fallback semantics."""

    def __init__(self, fallback_cookie_token: str | None = None) -> None:
        self._fallback_cookie_token = fallback_cookie_token

    def get_token_from_cookie(self, request: Request) -> str | None:
        cookie = request.cookies.get(COOKIE_TOKEN)
        return cookie if cookie is not None else self._fallback_cookie_token


RequestFactory = Callable[..., Request]
OauthFactory = Callable[[Optional[str]], DummyOauth]


@pytest.fixture
def request_factory() -> RequestFactory:
    return _build_request


@pytest.fixture
def oauth() -> DummyOauth:
    return DummyOauth()


@pytest.fixture
def oauth_factory() -> OauthFactory:
    def _factory(cookie_token: Optional[str] = None) -> DummyOauth:
        return DummyOauth(fallback_cookie_token=cookie_token)

    return _factory


@pytest.mark.parametrize(
    "headers, expected",
    [
        ({"cookie": f"{COOKIE_TOKEN}=cookie-123"}, "cookie-123"),
        ({"authorization": "Bearer header-456"}, "header-456"),
    ],
)
def test_token_from_request_prefers_cookie_or_header(
    request_factory: RequestFactory,
    oauth: DummyOauth,
    headers: dict[str, str],
    expected: str,
) -> None:
    req = request_factory(headers=headers)

    token = _token_from_request(req, oauth, allow_cookie=True)

    assert token == expected


def test_token_from_request_cookie_disabled_uses_header(
    request_factory: RequestFactory,
    oauth_factory: OauthFactory,
) -> None:
    req = request_factory(
        headers=(
            ("authorization", "Bearer hdr-789"),
            ("cookie", f"{COOKIE_TOKEN}=cookie-should-be-ignored"),
        )
    )
    oauth = oauth_factory("cookie-should-be-ignored")

    token = _token_from_request(req, oauth, allow_cookie=False)

    assert token == "hdr-789"


def test_token_from_request_no_token_returns_none(
    request_factory: RequestFactory,
    oauth: DummyOauth,
) -> None:
    req = request_factory()

    token = _token_from_request(req, oauth, allow_cookie=True)

    assert token is None


@pytest.mark.parametrize(
    "header",
    [
        "Bearer",  # missing token
        "Basic abc",  # wrong scheme
        "Bearer ",  # empty token
    ],
)
def test_invalid_authorization_header_returns_none(
    request_factory: RequestFactory,
    oauth: DummyOauth,
    header: str,
) -> None:
    req = request_factory(headers={"authorization": header})

    token = _token_from_request(req, oauth, allow_cookie=True)

    assert token is None


def test_cookie_wins_over_invalid_header(
    request_factory: RequestFactory,
    oauth: DummyOauth,
) -> None:
    req = request_factory(
        headers={
            "cookie": f"{COOKIE_TOKEN}=cookie-123",
            "authorization": "invalid",
        }
    )

    token = _token_from_request(req, oauth, allow_cookie=True)

    assert token == "cookie-123"
