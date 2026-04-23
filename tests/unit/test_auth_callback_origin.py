from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from launchpad.auth.api import callback
from launchpad.errors import Forbidden, Unauthorized


def make_request(
    method: str, headers: dict[str, str], client_id: str
) -> SimpleNamespace:
    """Create a minimal request-like object used by the callback handler.

    The object provides .method, .headers and .app with the minimal
    configuration consumed by the handler.
    """
    app = SimpleNamespace()
    app.config = SimpleNamespace()
    # Provide both self_domain and web_app_domain to match production config
    app.config.apolo = SimpleNamespace(
        self_domain="https://example.com", web_app_domain="https://example.com"
    )
    app.config.keycloak = SimpleNamespace(client_id=client_id)
    # http is passed to token_from_string; tests patch token_from_string so
    # this can be a dummy object.
    app.http = SimpleNamespace()

    req = SimpleNamespace()
    req.method = method
    req.headers = headers
    req.app = app
    return req


@pytest.mark.asyncio
async def test_post_callback_missing_origin_rejected() -> None:
    """If Origin/Referer are missing the POST should be rejected (CSRF)."""
    req = make_request("POST", headers={}, client_id="client-id")
    oauth = SimpleNamespace(set_auth_cookie=MagicMock())

    with pytest.raises(Forbidden):
        await callback(req, oauth)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_post_callback_invalid_authorization_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With valid Origin but missing/invalid Authorization header
    the endpoint should raise Unauthorized.
    """
    headers = {"origin": "https://example.com", "Authorization": "NoBearer"}
    req = make_request("POST", headers=headers, client_id="client-id")
    oauth = SimpleNamespace(set_auth_cookie=MagicMock())

    with pytest.raises(Unauthorized):
        await callback(req, oauth)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_post_callback_sets_cookie_on_valid_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Origin and Authorization are valid the handler should call
    oauth.set_auth_cookie and return a 200 Response.
    """
    headers = {"origin": "https://example.com", "Authorization": "Bearer mytoken"}
    req = make_request("POST", headers=headers, client_id="my-client")

    # Patch token_from_string to return a decoded token with matching azp
    async def fake_token_from_string(
        *, http: Any, keycloak_config: Any, access_token: str
    ) -> dict[str, Any]:
        # ensure the called access_token matches the header value
        assert access_token == "mytoken"
        return {"email": "me@example.com", "azp": "my-client"}

    monkeypatch.setattr("launchpad.auth.api.token_from_string", fake_token_from_string)

    oauth = SimpleNamespace(set_auth_cookie=MagicMock())

    resp = await callback(req, oauth)  # type: ignore[arg-type]

    # oauth.set_auth_cookie must be called with the response and token
    oauth.set_auth_cookie.assert_called_once()
    called_args = oauth.set_auth_cookie.call_args[0]
    assert called_args[1] == "mytoken"
    assert resp.status_code == 200
