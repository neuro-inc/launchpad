from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.responses import RedirectResponse

from launchpad.apps.service import AppService
from launchpad.auth import HEADER_X_FORWARDED_HOST, HEADER_X_FORWARDED_URI
from launchpad.auth.api import view_post_authorize
from launchpad.auth.oauth import Oauth
from launchpad.auth.static_hostname import StaticHostnameAuthService
from launchpad.auth.static_hostname_api import (
    finish_static_hostname_login,
    start_static_hostname_login,
)
from launchpad.errors import Forbidden
from launchpad.ext.apps_api import AppsApiError


@pytest.fixture
def mock_request() -> MagicMock:
    mock_request = MagicMock()
    mock_request.headers = {HEADER_X_FORWARDED_HOST: "silverfin-dev.apps.apolo.us"}
    mock_request.cookies = {}
    mock_request.app.config.auth_bypass_path_prefixes = []
    return mock_request


@pytest.fixture
def app_service() -> MagicMock:
    service = MagicMock(spec=AppService)
    service.resolve_app_for_authorization = AsyncMock(
        return_value=SimpleNamespace(
            app_id=uuid4(),
            is_shared=False,
            user_id="owner@example.test",
        )
    )
    return service


@pytest.fixture
def static_hostname_auth() -> MagicMock:
    service = MagicMock(spec=StaticHostnameAuthService)
    service.nonce_cookie = "__Host-launchpad-test-nonce"
    service.session_cookie = "__Host-launchpad-test-session"
    service.callback_path = "/_apolo/launchpad/test/handoff"
    service.begin = AsyncMock(return_value=("login", "nonce"))
    service.get_token = AsyncMock(return_value=None)
    service.redeem = AsyncMock(return_value="opaque-session")
    service.issue = AsyncMock(return_value="grant")
    return service


@pytest.fixture
def oauth() -> MagicMock:
    oauth = MagicMock(spec=Oauth)
    oauth.covers_hostname.return_value = False
    oauth.auth_base_url = "https://launchpad.apps.imdc.org.apolo.us/auth"
    oauth.redirect.return_value = RedirectResponse("https://keycloak.example/auth")
    return oauth


async def test_alias_login_starts_on_launchpad_origin_with_host_only_nonce(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
) -> None:
    response = await view_post_authorize(
        mock_request, app_service, oauth, static_hostname_auth
    )
    assert (
        response.headers["location"]
        == f"{oauth.auth_base_url}/static-hostname/start?login=login"
    )
    cookie = response.headers["set-cookie"]
    assert "__Host-launchpad-test-nonce=nonce" in cookie
    assert "Domain=" not in cookie
    assert all(
        value in cookie for value in ["Secure", "HttpOnly", "Path=/", "SameSite=lax"]
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    oauth.redirect.assert_not_called()
    app_service.resolve_app_for_authorization.assert_awaited_once_with(
        "silverfin-dev.apps.apolo.us",
    )


async def test_alias_handoff_sets_opaque_host_only_session(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
) -> None:
    mock_request.headers[HEADER_X_FORWARDED_URI] = (
        static_hostname_auth.callback_path + "?grant=grant"
    )
    mock_request.cookies[static_hostname_auth.nonce_cookie] = "nonce"
    response = await view_post_authorize(
        mock_request, app_service, oauth, static_hostname_auth
    )
    assert response.headers["location"] == "https://silverfin-dev.apps.apolo.us/"
    cookie = response.headers.getlist("set-cookie")[0]
    assert "opaque-session" in cookie and "Domain=" not in cookie
    assert "Secure" in cookie and "HttpOnly" in cookie and "Path=/" in cookie
    assert "Max-Age=0" in response.headers.getlist("set-cookie")[1]
    static_hostname_auth.redeem.assert_awaited_once_with(
        "grant",
        "nonce",
        "silverfin-dev.apps.apolo.us",
        app_service.resolve_app_for_authorization.return_value.app_id,
    )


@pytest.mark.parametrize("error", [None, AppsApiError()])
async def test_alias_detach_or_lookup_failure_is_denied(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
    error: AppsApiError | None,
) -> None:
    app_service.resolve_app_for_authorization.return_value = None
    app_service.resolve_app_for_authorization.side_effect = error
    with pytest.raises(HTTPException) as caught:
        await view_post_authorize(
            mock_request, app_service, oauth, static_hostname_auth
        )
    assert caught.value.status_code == (503 if error else 403)
    static_hostname_auth.begin.assert_not_awaited()
    static_hostname_auth.redeem.assert_not_awaited()


@pytest.mark.parametrize(
    "email,allowed", [("owner@example.test", True), ("other@example.test", False)]
)
async def test_alias_session_enforces_existing_owner_permissions(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
    email: str,
    allowed: bool,
) -> None:
    mock_request.cookies[static_hostname_auth.session_cookie] = "opaque-session"
    static_hostname_auth.get_token.return_value = "server-side-token"
    with patch(
        "launchpad.auth.dependencies.token_from_string",
        new=AsyncMock(return_value={"email": email}),
    ):
        if allowed:
            response = await view_post_authorize(
                mock_request, app_service, oauth, static_hostname_auth
            )
            assert response.status_code == 200
        else:
            with pytest.raises(Forbidden):
                await view_post_authorize(
                    mock_request, app_service, oauth, static_hostname_auth
                )
    static_hostname_auth.begin.assert_not_awaited()


async def test_start_static_hostname_login_uses_registered_oauth_callback(
    app_service: MagicMock, static_hostname_auth: MagicMock, oauth: MagicMock
) -> None:
    installed = app_service.resolve_app_for_authorization.return_value
    static_hostname_auth.read_login = AsyncMock(
        return_value=SimpleNamespace(
            hostname="silverfin-dev.apps.apolo.us",
            app_id=installed.app_id,
        )
    )
    response = await start_static_hostname_login(
        "login", app_service, static_hostname_auth, oauth
    )
    assert response.headers["location"] == "https://keycloak.example/auth"
    oauth.redirect.assert_called_once_with(
        original_redirect_uri=f"{oauth.auth_base_url}/static-hostname/finish?login=login",
    )


@pytest.mark.parametrize("moved", [False, True])
async def test_finish_static_hostname_login_checks_permission_and_binding(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
    moved: bool,
) -> None:
    installed = app_service.resolve_app_for_authorization.return_value
    static_hostname_auth.read_login = AsyncMock(
        return_value=SimpleNamespace(
            hostname="silverfin-dev.apps.apolo.us",
            app_id=uuid4() if moved else installed.app_id,
        )
    )
    expiry = (datetime.now(UTC) + timedelta(hours=1)).timestamp()
    with (
        patch(
            "launchpad.auth.static_hostname_api.get_raw_token_from_request",
            return_value="server-token",
        ) as extract_token,
        patch(
            "launchpad.auth.static_hostname_api.token_from_string",
            new=AsyncMock(
                return_value={
                    "email": "owner@example.test",
                    "exp": expiry,
                }
            ),
        ) as decode_token,
    ):
        if moved:
            with pytest.raises(Forbidden):
                await finish_static_hostname_login(
                    mock_request, "login", app_service, static_hostname_auth, oauth
                )
            static_hostname_auth.issue.assert_not_awaited()
        else:
            response = await finish_static_hostname_login(
                mock_request, "login", app_service, static_hostname_auth, oauth
            )
            extract_token.assert_called_once_with(mock_request, oauth)
            decode_token.assert_awaited_once_with(
                mock_request.app.http, mock_request.app.config.keycloak, "server-token"
            )
            assert (
                response.headers["location"]
                == "https://silverfin-dev.apps.apolo.us/_apolo/launchpad/test/handoff?grant=grant"
            )
            assert "server-token" not in response.headers["location"]
            static_hostname_auth.issue.assert_awaited_once_with(
                "login",
                "server-token",
                datetime.fromtimestamp(expiry, UTC),
                "owner@example.test",
            )


@pytest.mark.parametrize("endpoint", ["authorize", "start", "finish"])
async def test_static_host_lookup_failure_returns_unavailable(
    endpoint: str,
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
) -> None:
    static_hostname_auth.read_login = AsyncMock(
        return_value=SimpleNamespace(hostname="silverfin-dev.apps.apolo.us")
    )
    app_service.resolve_app_for_authorization.side_effect = AppsApiError()
    with pytest.raises(HTTPException) as caught:
        if endpoint == "authorize":
            await view_post_authorize(
                mock_request, app_service, oauth, static_hostname_auth
            )
        elif endpoint == "start":
            await start_static_hostname_login(
                "login", app_service, static_hostname_auth, oauth
            )
        else:
            await finish_static_hostname_login(
                mock_request, "login", app_service, static_hostname_auth, oauth
            )
    assert caught.value.status_code == 503
    static_hostname_auth.issue.assert_not_awaited()
    static_hostname_auth.redeem.assert_not_awaited()


async def test_empty_alias_session_skips_database() -> None:
    database = MagicMock()
    service = StaticHostnameAuthService(database, uuid4())
    assert await service.get_token("", "silverfin-dev.apps.apolo.us", uuid4()) is None
    database.assert_not_called()


@pytest.mark.parametrize(
    "expiry", [None, "123", True, False, 0, float("nan"), float("inf"), 1e100, -1e100]
)
async def test_finish_static_hostname_login_rejects_invalid_expiry(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
    expiry: object,
) -> None:
    installed = app_service.resolve_app_for_authorization.return_value
    static_hostname_auth.read_login = AsyncMock(
        return_value=SimpleNamespace(
            hostname="silverfin-dev.apps.apolo.us", app_id=installed.app_id
        )
    )
    with (
        patch(
            "launchpad.auth.static_hostname_api.get_raw_token_from_request",
            return_value="server-token",
        ),
        patch(
            "launchpad.auth.static_hostname_api.token_from_string",
            new=AsyncMock(return_value={"email": "owner@example.test", "exp": expiry}),
        ),
        pytest.raises(Forbidden),
    ):
        await finish_static_hostname_login(
            mock_request, "login", app_service, static_hostname_auth, oauth
        )
    static_hostname_auth.issue.assert_not_awaited()


async def test_invalid_forwarded_hostname_is_denied_before_lookup(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
) -> None:
    mock_request.headers[HEADER_X_FORWARDED_HOST] = "user@silverfin-dev.apps.apolo.us"
    with pytest.raises(Forbidden):
        await view_post_authorize(
            mock_request, app_service, oauth, static_hostname_auth
        )
    app_service.resolve_app_for_authorization.assert_not_awaited()


@pytest.mark.parametrize(
    "hostname,expected",
    [
        ("SILVERFIN-DEV.APPS.APOLO.US.:443", "silverfin-dev.apps.apolo.us"),
        ("silverfin-dev.apps.apolo.us.:8443", "silverfin-dev.apps.apolo.us:8443"),
    ],
)
async def test_noncanonical_origin_redirects_before_setting_nonce(
    mock_request: MagicMock,
    app_service: MagicMock,
    static_hostname_auth: MagicMock,
    oauth: MagicMock,
    hostname: str,
    expected: str,
) -> None:
    mock_request.headers[HEADER_X_FORWARDED_HOST] = hostname
    mock_request.headers[HEADER_X_FORWARDED_URI] = "/path?next=https://other.example"
    response = await view_post_authorize(
        mock_request, app_service, oauth, static_hostname_auth
    )
    assert (
        response.headers["location"]
        == f"https://{expected}/path?next=https://other.example"
    )
    assert "set-cookie" not in response.headers
    static_hostname_auth.begin.assert_not_awaited()
    static_hostname_auth.redeem.assert_not_awaited()
