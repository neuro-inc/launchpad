from __future__ import annotations

import asyncio
import json
import uuid
from time import time
from typing import Callable, Iterable, Optional
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.requests import Request
from yarl import URL

from launchpad.auth import dependencies
from launchpad.auth.dependencies import (
    get_raw_token_from_request as _token_from_request,
    token_from_string,
)
from launchpad.auth.oauth import Oauth
from launchpad.config import KeycloakConfig
from launchpad.errors import Unauthorized


_TEST_APP_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_TEST_COOKIE_TOKEN = f"launchpad-{_TEST_APP_ID.hex}-token"


async def test_token_verifier_rejects_non_rs256_before_loading_jwks() -> None:
    http = MagicMock()
    config = KeycloakConfig(url=URL("https://keycloak.example.test"), realm="launchpad")
    token = jwt.encode({}, "test-key-" * 4, algorithm="HS256", headers={"kid": "test"})

    with pytest.raises(Unauthorized):
        await token_from_string(http, config, token)

    http.get.assert_not_called()


async def test_token_verifier_reuses_keys_and_refreshes_on_rotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = KeycloakConfig(url=URL("https://keycloak.example.test"), realm="launchpad")
    claims = {"iss": f"{config.url}/realms/{config.realm}", "aud": "account"}
    old_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def jwk(key: rsa.RSAPrivateKey, kid: str) -> dict[str, object]:
        return {
            **json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())),
            "kid": kid,
        }

    def token(key: rsa.RSAPrivateKey, kid: str, *, expires: bool = True) -> str:
        payload = {**claims, "exp": int(time()) + 60} if expires else claims
        return jwt.encode(payload, key, algorithm="RS256", headers={"kid": kid})

    old_token, new_token = token(old_key, "old"), token(new_key, "new")
    published = [jwk(old_key, "old")]
    now = 100.0
    monkeypatch.setattr(dependencies, "monotonic", lambda: now)
    http = MagicMock()

    async def response_json() -> dict[str, object]:
        await asyncio.sleep(0)
        return {"keys": published}

    http.get.return_value.__aenter__.return_value = MagicMock(
        json=AsyncMock(side_effect=response_json)
    )

    assert (await token_from_string(http, config, old_token))["aud"] == "account"
    with pytest.raises(Unauthorized):
        await token_from_string(http, config, token(old_key, "old", expires=False))
    with pytest.raises(Unauthorized):
        await token_from_string(http, config, new_token)
    assert http.get.call_count == 1

    now += 5
    published = [jwk(old_key, "old"), jwk(new_key, "new")]
    await asyncio.gather(
        token_from_string(http, config, new_token),
        token_from_string(http, config, new_token),
    )
    await token_from_string(http, config, old_token)
    assert http.get.call_count == 2

    now += 61
    published = [jwk(new_key, "new")]
    with pytest.raises(Unauthorized):
        await token_from_string(http, config, old_token)
    await token_from_string(http, config, new_token)
    assert http.get.call_count == 3


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
        self._cookie_token = _TEST_COOKIE_TOKEN
        self._fallback_cookie_token = fallback_cookie_token

    def get_token_from_cookie(self, request: Request) -> str | None:
        cookie = request.cookies.get(self._cookie_token)
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
        ({"cookie": f"{_TEST_COOKIE_TOKEN}=cookie-123"}, "cookie-123"),
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
            ("cookie", f"{_TEST_COOKIE_TOKEN}=cookie-should-be-ignored"),
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
            "cookie": f"{_TEST_COOKIE_TOKEN}=cookie-123",
            "authorization": "invalid",
        }
    )

    token = _token_from_request(req, oauth, allow_cookie=True)

    assert token == "cookie-123"
