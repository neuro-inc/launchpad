from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from aiohttp import ClientSession
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from yarl import URL

from launchpad.apps.models import InstalledApp
from launchpad.auth import HEADER_X_FORWARDED_HOST
from launchpad.auth.api import view_post_authorize
from launchpad.auth.dependencies import token_from_string
from launchpad.auth.oauth import Oauth
from launchpad.config import KeycloakConfig
from launchpad.errors import Forbidden, Unauthorized


def _record_attr(record: logging.LogRecord, name: str) -> object:
    return getattr(record, name)


def _make_authorize_request(*, forwarded_host: str) -> MagicMock:
    req = MagicMock(spec=Request)
    req.headers = {HEADER_X_FORWARDED_HOST: forwarded_host}
    req.method = "GET"
    req.url = URL(f"https://launchpad.example/auth/authorize?target={forwarded_host}")
    req.state = MagicMock()
    req.state.request_id = "req-123"
    req.state.correlation_id = "corr-456"
    req.app = MagicMock()
    req.app.http = AsyncMock(spec=ClientSession)
    req.app.config = MagicMock()
    req.app.config.keycloak = KeycloakConfig(
        url=URL("https://keycloak.example"),
        realm="example",
    )
    return req


async def test_authorize_redirects_to_oauth_when_token_missing_or_invalid(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    request = _make_authorize_request(forwarded_host="app.example.com")
    app = MagicMock(spec=InstalledApp)
    app.launchpad_app_name = "demo"
    app.app_id = uuid4()
    app.is_shared = False
    app.user_id = "owner@example.com"

    async def fake_select_app_by_any_url(db: object, url: str) -> InstalledApp:
        assert url == "https://app.example.com"
        return app

    async def fake_decode_token_from_request(
        request: object, oauth: object
    ) -> dict[str, str]:
        raise Unauthorized(reason_code="TOKEN_MISSING", branch="tests.token_missing")

    monkeypatch.setattr(
        "launchpad.auth.api.select_app_by_any_url", fake_select_app_by_any_url
    )
    monkeypatch.setattr(
        "launchpad.auth.api.decode_token_from_request", fake_decode_token_from_request
    )
    monkeypatch.setattr(
        "launchpad.auth.api.get_raw_token_from_request",
        lambda request, oauth, allow_cookie=True: None,
    )

    caplog.set_level(logging.INFO)
    redirect_calls: list[str] = []

    class OauthMock(Oauth):
        def redirect(self, original_redirect_uri: str) -> RedirectResponse:
            redirect_calls.append(original_redirect_uri)
            return RedirectResponse(url="https://idp.example/auth")

    oauth = Mock(spec=Oauth)
    oauth.get_token_from_cookie.return_value = None
    oauth.redirect.side_effect = lambda original_redirect_uri: OauthMock(
        http=AsyncMock(spec=ClientSession),
        keycloak_config=KeycloakConfig(
            url=URL("https://keycloak.example"), realm="example"
        ),
        cookie_domain="example.com",
        launchpad_domain="app.example.com",
    ).redirect(original_redirect_uri)
    db = AsyncMock(spec=AsyncSession)
    response = await view_post_authorize(request, db=db, oauth=oauth)

    assert response.status_code == 307
    assert redirect_calls == ["https://app.example.com"]
    redirect_record = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "launchpad.auth.reauthorization.required"
    )
    assert _record_attr(redirect_record, "decision") == "redirect_to_auth"
    assert _record_attr(redirect_record, "reason_code") == "TOKEN_MISSING"
    assert _record_attr(redirect_record, "token_present") is False
    assert _record_attr(redirect_record, "target_app_host") == "app.example.com"


async def test_authorize_denies_access_for_private_app_non_owner(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    request = _make_authorize_request(forwarded_host="private.example.com")
    app = MagicMock(spec=InstalledApp)
    app.launchpad_app_name = "private-app"
    app.app_id = uuid4()
    app.is_shared = False
    app.user_id = "owner@example.com"

    async def fake_select_app_by_any_url(db: object, url: str) -> InstalledApp:
        assert url == "https://private.example.com"
        return app

    async def fake_decode_token_from_request(
        request: object, oauth: object
    ) -> dict[str, str]:
        return {
            "email": "attacker@example.com",
            "preferred_username": "attacker",
            "azp": "frontend",
            "aud": "account",
        }

    monkeypatch.setattr(
        "launchpad.auth.api.select_app_by_any_url", fake_select_app_by_any_url
    )
    monkeypatch.setattr(
        "launchpad.auth.api.decode_token_from_request", fake_decode_token_from_request
    )
    monkeypatch.setattr(
        "launchpad.auth.api.get_raw_token_from_request",
        lambda request, oauth, allow_cookie=True: "header-token",
    )

    caplog.set_level(logging.INFO)
    oauth = Mock(spec=Oauth)
    oauth.redirect.side_effect = lambda original_redirect_uri: RedirectResponse(
        url=original_redirect_uri
    )
    db = AsyncMock(spec=AsyncSession)
    with pytest.raises(Forbidden):
        await view_post_authorize(request, db=db, oauth=oauth)
    deny_record = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "launchpad.auth.forwardauth.denied"
    )
    assert _record_attr(deny_record, "reason_code") == "APP_ACCESS_DENIED"
    assert _record_attr(deny_record, "decision") == "deny"
    assert _record_attr(deny_record, "user_id_hash")


async def test_token_from_string_logs_fingerprint_on_kid_mismatch(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fake_get_jwks(
        *, http: object, keycloak_config: object, kid: str
    ) -> dict[str, list[dict[str, str]]]:
        return {"keys": [{"kid": "different-kid", "kty": "RSA"}]}

    class _FakeAlg:
        def from_jwk(self, key: dict[str, str]) -> object:
            return object()

    monkeypatch.setattr(
        "launchpad.auth.dependencies.jwt.get_unverified_header",
        lambda token: {"kid": "missing-kid", "alg": "RS256"},
    )
    monkeypatch.setattr(
        "launchpad.auth.dependencies.jwt.get_algorithm_by_name",
        lambda alg: _FakeAlg(),
    )
    monkeypatch.setattr("launchpad.auth.dependencies._get_jwks", fake_get_jwks)

    caplog.set_level(logging.ERROR)

    http = AsyncMock(spec=ClientSession)
    keycloak_config = KeycloakConfig(
        url=URL("https://keycloak.example"),
        realm="example",
    )
    with pytest.raises(Unauthorized):
        await token_from_string(
            http=http,
            keycloak_config=keycloak_config,
            access_token="secret-token-value",
        )

    record = next(r for r in caplog.records if r.msg == "jwt_kid_not_found_in_jwks")
    assert getattr(record, "event_name") == "launchpad.auth.token.validation_failed"
    assert getattr(record, "reason_code") == "KID_NOT_FOUND"
    assert getattr(record, "token_fingerprint")
    assert "secret-token-value" not in caplog.text


async def test_authorize_redirect_logs_expired_cookie_reason(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    request = _make_authorize_request(forwarded_host="expired.example.com")
    app = MagicMock(spec=InstalledApp)
    app.launchpad_app_name = "expired-demo"
    app.app_id = uuid4()
    app.is_shared = True
    app.user_id = "owner@example.com"

    async def fake_select_app_by_any_url(db: object, url: str) -> InstalledApp:
        assert url == "https://expired.example.com"
        return app

    async def fake_decode_token_from_request(
        request: object, oauth: object
    ) -> dict[str, str]:
        raise Unauthorized(reason_code="TOKEN_EXPIRED", branch="tests.expired")

    monkeypatch.setattr(
        "launchpad.auth.api.select_app_by_any_url", fake_select_app_by_any_url
    )
    monkeypatch.setattr(
        "launchpad.auth.api.decode_token_from_request", fake_decode_token_from_request
    )
    monkeypatch.setattr(
        "launchpad.auth.api.get_raw_token_from_request",
        lambda request, oauth, allow_cookie=True: "expired-cookie-token",
    )

    caplog.set_level(logging.INFO)
    oauth = Mock(spec=Oauth)
    oauth.get_token_from_cookie.return_value = "expired-cookie-token"
    oauth.redirect.side_effect = lambda original_redirect_uri: RedirectResponse(
        url="https://idp.example/auth"
    )
    db = AsyncMock(spec=AsyncSession)

    response = await view_post_authorize(request, db=db, oauth=oauth)

    assert response.status_code == 307
    reauth_record = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "launchpad.auth.reauthorization.required"
    )
    assert _record_attr(reauth_record, "reason_code") == "TOKEN_EXPIRED"
    assert _record_attr(reauth_record, "token_present") is True
    assert _record_attr(reauth_record, "redirect_required") is True


async def test_authorize_redirect_logs_authorized_party_mismatch(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    request = _make_authorize_request(forwarded_host="azp.example.com")
    app = MagicMock(spec=InstalledApp)
    app.launchpad_app_name = "azp-demo"
    app.app_id = uuid4()
    app.is_shared = True
    app.user_id = "owner@example.com"

    async def fake_select_app_by_any_url(db: object, url: str) -> InstalledApp:
        assert url == "https://azp.example.com"
        return app

    async def fake_decode_token_from_request(
        request: object, oauth: object
    ) -> dict[str, str | list[str]]:
        return {
            "email": "owner@example.com",
            "preferred_username": "owner",
            "azp": "wrong-client",
            "aud": ["account"],
        }

    monkeypatch.setattr(
        "launchpad.auth.api.select_app_by_any_url", fake_select_app_by_any_url
    )
    monkeypatch.setattr(
        "launchpad.auth.api.decode_token_from_request", fake_decode_token_from_request
    )
    monkeypatch.setattr(
        "launchpad.auth.api.get_raw_token_from_request",
        lambda request, oauth, allow_cookie=True: "cookie-token",
    )

    caplog.set_level(logging.INFO)
    oauth = Mock(spec=Oauth)
    oauth.get_token_from_cookie.return_value = "cookie-token"
    oauth.redirect.side_effect = lambda original_redirect_uri: RedirectResponse(
        url="https://idp.example/auth"
    )
    db = AsyncMock(spec=AsyncSession)

    response = await view_post_authorize(request, db=db, oauth=oauth)

    assert response.status_code == 307
    redirect_record = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "launchpad.auth.forwardauth.redirected"
    )
    assert _record_attr(redirect_record, "reason_code") == "AUTHORIZED_PARTY_INVALID"
    assert _record_attr(redirect_record, "authorized_party_valid") is False


async def test_authorize_denies_when_forwardauth_host_header_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = MagicMock(spec=Request)
    request.headers = {}
    request.method = "GET"
    request.url = URL("https://launchpad.example/auth/authorize")
    request.state = MagicMock()
    request.state.request_id = "req-123"
    request.state.correlation_id = "corr-456"
    request.app = MagicMock()
    request.app.http = AsyncMock(spec=ClientSession)
    request.app.config = MagicMock()
    request.app.config.keycloak = KeycloakConfig(
        url=URL("https://keycloak.example"),
        realm="example",
    )

    caplog.set_level(logging.INFO)
    with pytest.raises(Unauthorized, match="Missing ForwardAuth host header"):
        await view_post_authorize(
            request,
            db=AsyncMock(spec=AsyncSession),
            oauth=Mock(spec=Oauth),
        )

    record = next(
        entry
        for entry in caplog.records
        if getattr(entry, "event", None) == "launchpad.auth.forwardauth.denied"
    )
    assert _record_attr(record, "reason_code") == "FORWARDAUTH_HOST_MISSING"
    assert _record_attr(record, "decision") == "deny"
