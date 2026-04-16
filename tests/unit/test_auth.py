import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError, ClientSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from yarl import URL

from launchpad.auth.dependencies import auth_required
from launchpad.auth.models import User
from launchpad.auth.oauth import COOKIE_CODE_VERIFIER, Oauth, OauthError, Retry
from launchpad.config import KeycloakConfig
from launchpad.errors import Forbidden, Unauthorized


@pytest.fixture
def mock_request() -> MagicMock:
    request = MagicMock(spec=Request)
    request.headers = {}
    request.query_params = {}
    request.cookies = {}
    request.state = MagicMock()
    request.app = MagicMock()
    return request


@pytest.fixture
def mock_keycloak_config() -> KeycloakConfig:
    return KeycloakConfig(
        url=URL("http://mock-keycloak.com"),
        realm="mock-realm",
        client_id="mock-client-id",
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
            await auth_required(request=mock_request)

        mock_token_from_request.assert_called_once_with(mock_request)


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


async def test_oauth_callback_success(
    oauth_instance: Oauth, mock_request: MagicMock, mock_http_session: AsyncMock
) -> None:
    """Successful callback exchanges code for token and sets cookie."""
    original_url = "https://original.example/path"
    state = base64.urlsafe_b64encode(original_url.encode()).decode()

    mock_request.query_params = {"code": "mock-code", "state": state}
    mock_request.cookies = {COOKIE_CODE_VERIFIER: "mock-code-verifier"}

    mock_response_obj = MagicMock()
    mock_response_obj.raise_for_status.return_value = None

    async def _json() -> dict[str, str]:
        return {"access_token": "mock-access-token"}

    mock_response_obj.json = _json
    mock_http_session.post.return_value.__aenter__.return_value = mock_response_obj

    oauth_instance._http = mock_http_session

    response = await oauth_instance.callback(mock_request)

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == original_url
    assert "launchpad-token" in response.headers.get("set-cookie", "")


async def test_auth_api_callback_delegates_success(mock_request: MagicMock) -> None:
    """`auth.api.callback` should delegate to oauth.callback and return
    the RedirectResponse produced by it.
    """
    from unittest.mock import AsyncMock

    from starlette.responses import RedirectResponse

    from launchpad.auth.api import callback as auth_callback

    mock_oauth = AsyncMock()
    mock_oauth.callback.return_value = RedirectResponse("https://example.com/success")

    response = await auth_callback(mock_request, mock_oauth)
    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "https://example.com/success"


async def test_auth_api_callback_handles_oauth_error(mock_request: MagicMock) -> None:
    """When the oauth backend raises OauthError the handler should raise Forbidden."""
    from unittest.mock import AsyncMock

    from launchpad.auth.api import callback as auth_callback

    mock_oauth = AsyncMock()
    mock_oauth.callback.side_effect = OauthError("failed")

    import pytest

    with pytest.raises(Forbidden):
        await auth_callback(mock_request, mock_oauth)


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


async def test_oauth_fetch_token_server_error_raises_retry(
    oauth_instance: Oauth, mock_request: MagicMock, mock_http_session: AsyncMock
) -> None:
    """If Keycloak responds with a 5xx the internal code should raise Retry
    (the backoff decorator handles retries). Call the wrapped function to
    assert the Retry path is taken.
    """
    mock_response_obj = MagicMock()
    mock_response_obj.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(), history=(), status=500, message="Server Error"
    )
    mock_http_session.post.return_value.__aenter__.return_value = mock_response_obj

    data = {"grant_type": "authorization_code"}

    from typing import Any, cast

    with pytest.raises(Retry):
        # The _fetch_token method is decorated with backoff.on_exception;
        # access the original wrapped function via __wrapped__. Use a cast
        # to Any to satisfy mypy about the attribute.
        original = cast(Any, oauth_instance._fetch_token).__wrapped__
        await original(oauth_instance, data)


async def test_oauth_start_method(
    oauth_instance: Oauth, mock_request: MagicMock
) -> None:
    """Oauth.start_auth should redirect to Keycloak and preserve original URL
    in the state parameter."""
    mock_request.url = URL("https://original.com/path")

    response = oauth_instance.start_auth(mock_request)

    assert isinstance(response, RedirectResponse)

    redirect_url = URL(response.headers["location"])
    assert redirect_url.host == "mock-keycloak.com"
    assert redirect_url.path == "/realms/mock-realm/protocol/openid-connect/auth"

    state = redirect_url.query["state"]
    decoded = base64.urlsafe_b64decode(state.encode()).decode()
    assert decoded == "https://original.com/path"


async def test_auth_api_start_handler(
    oauth_instance: Oauth, mock_request: MagicMock
) -> None:
    """auth.api.start_auth handler delegates to Oauth.start_auth and
    returns a RedirectResponse."""
    from launchpad.auth.api import start_auth as start_auth_route

    mock_request.url = URL("https://example.com/foo")

    response = await start_auth_route(mock_request, oauth_instance)
    assert isinstance(response, RedirectResponse)
    redirect_url = URL(response.headers["location"])
    assert redirect_url.path.endswith("/auth")
