from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError, ClientSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from yarl import URL

from launchpad.auth.dependencies import auth_required
from launchpad.auth.models import User
from launchpad.auth.oauth import COOKIE_CODE_VERIFIER, Oauth, OauthError
from launchpad.config import KeycloakConfig
from launchpad.errors import Forbidden, Unauthorized


@pytest.fixture
def mock_request() -> SimpleNamespace:
    request = SimpleNamespace()
    request.headers = {}
    request.query_params = {}
    request.cookies = {}
    request.state = MagicMock()
    request.app = SimpleNamespace(
        config=SimpleNamespace(
            keycloak=SimpleNamespace(
                idp_hint=None,
                required_identity_source=None,
                required_identity_group=None,
            )
        )
    )
    return request


@pytest.fixture
def mock_keycloak_config() -> KeycloakConfig:
    return KeycloakConfig(
        url=URL("http://mock-keycloak.com"),
        realm="mock-realm",
        client_id="mock-client-id",
        idp_hint=None,
        required_identity_source=None,
        required_identity_group=None,
    )


@pytest.fixture
def mock_http_session() -> AsyncMock:
    return AsyncMock(spec=ClientSession)


@pytest.fixture
def oauth_instance(
    mock_keycloak_config: KeycloakConfig, mock_http_session: AsyncMock
) -> Oauth:
    return Oauth(
        http=mock_http_session,
        keycloak_config=mock_keycloak_config,
        cookie_domain="mock-cookie.com",
        launchpad_domain="mock-launchpad.com",
    )


async def test_auth_required_success(mock_request: MagicMock) -> None:
    mock_request.headers["Authorization"] = "Bearer valid-token"
    # Patch _token_from_request to return a decoded token
    with patch(
        "launchpad.auth.dependencies._token_from_request", new=AsyncMock()
    ) as mock_token_from_request:
        mock_token_from_request.return_value = {
            "email": "test-user-id",
            "name": "testuser",
        }

        user = await auth_required(request=mock_request)

        assert isinstance(user, User)
        assert user.id == "test-user-id"
        assert user.email == "test-user-id"
        assert user.name == "testuser"
        mock_token_from_request.assert_called_once_with(
            mock_request
        )  # Corrected assertion


async def test_auth_required_no_authorization_header(mock_request: MagicMock) -> None:
    with pytest.raises(Unauthorized, match="Unathorized"):
        await auth_required(request=mock_request)

    # Ensure _token_from_request is not called
    with patch(
        "launchpad.auth.dependencies._token_from_request", new=AsyncMock()
    ) as mock_token_from_request:
        mock_token_from_request.assert_not_called()


async def test_auth_required_invalid_authorization_header(
    mock_request: MagicMock,
) -> None:
    mock_request.headers["Authorization"] = "InvalidToken"

    with pytest.raises(Unauthorized, match="Unathorized"):
        await auth_required(request=mock_request)

    # Ensure _token_from_request is not called
    with patch(
        "launchpad.auth.dependencies._token_from_request", new=AsyncMock()
    ) as mock_token_from_request:
        mock_token_from_request.assert_not_called()


async def test_auth_required_invalid_token(mock_request: MagicMock) -> None:
    mock_request.headers["Authorization"] = "Bearer invalid-token"
    # Patch _token_from_request to raise an exception
    with patch(
        "launchpad.auth.dependencies._token_from_request", new=AsyncMock()
    ) as mock_token_from_request:
        mock_token_from_request.side_effect = Unauthorized("Token decoding failed")

        with pytest.raises(Unauthorized, match="Token decoding failed"):
            await auth_required(request=cast(Request, mock_request))

        mock_token_from_request.assert_called_once_with(mock_request)


async def test_auth_required_requires_procore_identity_when_configured(
    mock_request: SimpleNamespace,
) -> None:
    mock_request.headers["Authorization"] = "Bearer valid-token"
    mock_request.app.config.keycloak.required_identity_source = "procore"
    mock_request.app.config.keycloak.required_identity_group = "/procore-users"

    with patch(
        "launchpad.auth.dependencies._token_from_request", new=AsyncMock()
    ) as mock_token_from_request:
        mock_token_from_request.return_value = {
            "email": "test-user-id",
            "name": "testuser",
            "groups": ["/procore-users"],
        }

        with pytest.raises(Forbidden, match="ProCore identity is required"):
            await auth_required(request=cast(Request, mock_request))


async def test_auth_required_skips_procore_for_regular_user(
    mock_request: SimpleNamespace,
) -> None:
    mock_request.headers["Authorization"] = "Bearer valid-token"
    mock_request.app.config.keycloak.required_identity_source = "procore"
    mock_request.app.config.keycloak.required_identity_group = "/procore-users"

    with patch(
        "launchpad.auth.dependencies._token_from_request", new=AsyncMock()
    ) as mock_token_from_request:
        mock_token_from_request.return_value = {
            "email": "test-user-id",
            "name": "testuser",
            "groups": ["/support-users"],
        }

        user = await auth_required(request=cast(Request, mock_request))

        assert user.email == "test-user-id"


async def test_auth_required_skips_procore_for_admin_user(
    mock_request: SimpleNamespace,
) -> None:
    mock_request.headers["Authorization"] = "Bearer valid-token"
    mock_request.app.config.keycloak.required_identity_source = "procore"
    mock_request.app.config.keycloak.required_identity_group = "/procore-users"

    with patch(
        "launchpad.auth.dependencies._token_from_request", new=AsyncMock()
    ) as mock_token_from_request:
        mock_token_from_request.return_value = {
            "email": "admin@launchpad.com",
            "name": "admin",
            "realm_access": {"roles": ["admin"]},
        }

        user = await auth_required(request=cast(Request, mock_request))

        assert user.email == "admin@launchpad.com"


async def test_oauth_redirect(oauth_instance: Oauth, mock_request: MagicMock) -> None:
    original_redirect_uri = "https://original.com/path"
    response = oauth_instance.redirect(original_redirect_uri)

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307  # Temporary Redirect

    # Verify URL parameters
    redirect_url = URL(response.headers["location"])
    assert redirect_url.host == "mock-keycloak.com"
    assert redirect_url.path == "/realms/mock-realm/protocol/openid-connect/auth"
    assert redirect_url.query["client_id"] == "mock-client-id"
    assert redirect_url.query["response_type"] == "code"
    assert redirect_url.query["scope"] == "openid profile email offline_access"
    assert (
        redirect_url.query["redirect_uri"] == "https://mock-launchpad.com/auth/callback"
    )
    assert redirect_url.query["code_challenge_method"] == "S256"
    assert "code_challenge" in redirect_url.query
    assert "state" in redirect_url.query

    # Verify cookie
    assert COOKIE_CODE_VERIFIER in response.headers["set-cookie"]


async def test_oauth_callback_missing_params(
    oauth_instance: Oauth, mock_request: MagicMock
) -> None:
    # Test missing code
    mock_request.query_params = {"state": "mock-state"}
    mock_request.cookies = {COOKIE_CODE_VERIFIER: "mock-code-verifier"}
    with pytest.raises(OauthError, match="missing required params"):
        await oauth_instance.callback(mock_request)

    # Test missing state
    mock_request.query_params = {"code": "mock-code"}
    mock_request.cookies = {COOKIE_CODE_VERIFIER: "mock-code-verifier"}
    with pytest.raises(OauthError, match="missing required params"):
        await oauth_instance.callback(mock_request)

    # Test missing code_verifier cookie
    mock_request.query_params = {"code": "mock-code", "state": "mock-state"}
    mock_request.cookies = {}
    with pytest.raises(OauthError, match="missing required params"):
        await oauth_instance.callback(mock_request)


async def test_oauth_fetch_token_client_error(
    oauth_instance: Oauth,
    mock_request: MagicMock,
    mock_http_session: AsyncMock,
) -> None:
    mock_response_obj = MagicMock()
    mock_response_obj.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(), history=(), status=400, message="Bad Request"
    )
    mock_http_session.post.return_value.__aenter__.return_value = mock_response_obj

    data = {"grant_type": "authorization_code"}
    with pytest.raises(OauthError):
        await oauth_instance._fetch_token(data)


async def test_oauth_fetch_token_json_error(
    oauth_instance: Oauth,
    mock_request: MagicMock,
    mock_http_session: AsyncMock,
) -> None:
    mock_response_obj = MagicMock()
    mock_response_obj.json.side_effect = ValueError("Invalid JSON")
    mock_response_obj.raise_for_status.return_value = None
    mock_http_session.post.return_value.__aenter__.return_value = mock_response_obj

    data = {"grant_type": "authorization_code"}
    with pytest.raises(OauthError):
        await oauth_instance._fetch_token(data)


async def test_oauth_fetch_token_key_error(
    oauth_instance: Oauth,
    mock_request: MagicMock,
    mock_http_session: AsyncMock,
) -> None:
    mock_response_obj = MagicMock()
    mock_response_obj.json.return_value = {"wrong_key": "value"}
    mock_response_obj.raise_for_status.return_value = None
    mock_http_session.post.return_value.__aenter__.return_value = mock_response_obj

    data = {"grant_type": "authorization_code"}
    with pytest.raises(OauthError):
        await oauth_instance._fetch_token(data)


async def test_oauth_redirect_with_idp_hint(mock_http_session: AsyncMock) -> None:
    oauth = Oauth(
        http=mock_http_session,
        keycloak_config=KeycloakConfig(
            url=URL("http://mock-keycloak.com"),
            realm="mock-realm",
            client_id="mock-client-id",
            idp_hint="procore",
        ),
        cookie_domain="mock-cookie.com",
        launchpad_domain="mock-launchpad.com",
    )

    response = oauth.redirect("https://original.com/path")

    redirect_url = URL(response.headers["location"])
    assert redirect_url.query["kc_idp_hint"] == "procore"


async def test_oauth_redirect_with_required_procore_identity_does_not_force_broker(
    mock_http_session: AsyncMock,
) -> None:
    oauth = Oauth(
        http=mock_http_session,
        keycloak_config=KeycloakConfig(
            url=URL("http://mock-keycloak.com"),
            realm="mock-realm",
            client_id="mock-client-id",
            required_identity_source="procore",
            required_identity_group="/procore-users",
        ),
        cookie_domain="mock-cookie.com",
        launchpad_domain="mock-launchpad.com",
    )

    response = oauth.redirect("https://original.com/path")

    redirect_url = URL(response.headers["location"])
    assert "kc_idp_hint" not in redirect_url.query
