"""
Unit tests for cookie lifecycle management (creation, retrieval, deletion).
These tests verify that the "launchpad-token" cookie is properly set and managed
during the authentication process.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import RedirectResponse
from yarl import URL

from launchpad.auth.oauth import COOKIE_CODE_VERIFIER, COOKIE_TOKEN, Oauth
from launchpad.config import KeycloakConfig


@pytest.fixture
def mock_request() -> MagicMock:
    """Mock a Starlette request object"""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.query_params = {}
    request.cookies = {}
    request.state = MagicMock()
    request.app = MagicMock()
    return request


@pytest.fixture
def mock_keycloak_config() -> KeycloakConfig:
    """Mock Keycloak configuration"""
    return KeycloakConfig(
        url=URL("http://mock-keycloak.com"),
        realm="mock-realm",
        client_id="mock-client-id",
    )


@pytest.fixture
def mock_http_session() -> AsyncMock:
    """Mock aiohttp ClientSession"""
    return AsyncMock()


@pytest.fixture
def oauth_instance(
    mock_keycloak_config: KeycloakConfig, mock_http_session: AsyncMock
) -> Oauth:
    """Create an Oauth instance for testing"""
    return Oauth(
        http=mock_http_session,
        keycloak_config=mock_keycloak_config,
        cookie_domain="example.com",
        launchpad_domain="launchpad.example.com",
    )


class TestCookieRetrieval:
    """Tests for getting token from cookie"""

    def test_get_token_from_cookie_exists(
        self, oauth_instance: Oauth, mock_request: MagicMock
    ) -> None:
        """Test retrieving token when cookie exists"""
        mock_token = "test-jwt-token-12345"
        mock_request.cookies = {COOKIE_TOKEN: mock_token}

        token = oauth_instance.get_token_from_cookie(mock_request)

        assert token == mock_token

    def test_get_token_from_cookie_not_exists(
        self, oauth_instance: Oauth, mock_request: MagicMock
    ) -> None:
        """Test retrieving token when cookie does not exist"""
        mock_request.cookies = {}

        token = oauth_instance.get_token_from_cookie(mock_request)

        assert token is None

    def test_get_token_from_cookie_with_other_cookies(
        self, oauth_instance: Oauth, mock_request: MagicMock
    ) -> None:
        """Test retrieving token when other cookies exist"""
        mock_token = "test-jwt-token-12345"
        mock_request.cookies = {
            "other_cookie": "some-value",
            COOKIE_TOKEN: mock_token,
            "another_cookie": "another-value",
        }

        token = oauth_instance.get_token_from_cookie(mock_request)

        assert token == mock_token


class TestCookieLogging:
    """Tests for cookie-related logging"""

    def test_get_token_from_cookie_logs_success(
        self,
        oauth_instance: Oauth,
        mock_request: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that getting token from cookie produces debug log"""
        import logging

        mock_token = "test-jwt-token-12345"
        mock_request.cookies = {COOKIE_TOKEN: mock_token}

        with caplog.at_level(logging.DEBUG, logger="launchpad.auth.oauth"):
            token = oauth_instance.get_token_from_cookie(mock_request)

        assert token == mock_token
        assert "Cookie 'launchpad-token' retrieved from request" in caplog.text

    def test_get_token_from_cookie_logs_missing(
        self,
        oauth_instance: Oauth,
        mock_request: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that missing cookie produces debug log"""
        import logging

        mock_request.cookies = {}

        with caplog.at_level(logging.DEBUG, logger="launchpad.auth.oauth"):
            token = oauth_instance.get_token_from_cookie(mock_request)

        assert token is None
        assert "Cookie 'launchpad-token' not found in request" in caplog.text


class TestCookieCreationOnDirectLogin:
    """Tests for cookie creation in POST /token endpoint (direct login)"""

    def test_set_cookie_method_creates_cookie_with_correct_attributes(
        self, oauth_instance: Oauth
    ) -> None:
        """Test that _set_cookie properly sets cookie attributes"""
        from starlette.responses import Response

        response = Response()
        test_token = "test-jwt-token-12345"

        oauth_instance._set_cookie(response, key=COOKIE_TOKEN, value=test_token)

        # Verify set-cookie header is in response
        set_cookie_header = response.headers.get("set-cookie", "")
        assert COOKIE_TOKEN in set_cookie_header
        assert test_token in set_cookie_header
        assert "secure" in set_cookie_header.lower()
        assert "httponly" in set_cookie_header.lower()
        assert ".example.com" in set_cookie_header

    def test_post_token_endpoint_sets_cookie_with_domain(
        self,
        oauth_instance: Oauth,
    ) -> None:
        """Test that _set_cookie properly sets cookie attributes via OAuth instance"""
        from starlette.responses import Response

        response = Response()
        test_token = "test-jwt-token-12345"

        # Use the oauth instance to set the cookie
        oauth_instance._set_cookie(response, key=COOKIE_TOKEN, value=test_token)

        # Verify set-cookie header is in response
        set_cookie_header = response.headers.get("set-cookie", "")
        assert COOKIE_TOKEN in set_cookie_header
        assert test_token in set_cookie_header
        assert "secure" in set_cookie_header.lower()
        assert "httponly" in set_cookie_header.lower()
        assert ".example.com" in set_cookie_header


class TestSetAuthCookieEndpoint:
    """Tests for POST /auth/cookie endpoint"""

    def test_set_auth_cookie_with_valid_token(
        self,
    ) -> None:
        """Test that POST /auth/cookie sets the launchpad-token cookie"""
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi import FastAPI
        from starlette.testclient import TestClient

        from launchpad.auth.api import auth_router
        from launchpad.auth.oauth import Oauth
        from launchpad.config import KeycloakConfig

        # Create mock app config
        mock_keycloak_config = KeycloakConfig(
            url=URL("http://mock-keycloak.com"),
            realm="mock-realm",
            client_id="mock-client-id",
        )

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        # Create mock decoded token response
        mock_decoded_token: dict[str, object] = {
            "email": "test@example.com",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["user"]},
        }

        # Create mock JWT validation function
        async def mock_token_from_string(
            **kwargs: dict[str, object],
        ) -> dict[str, object]:
            return mock_decoded_token

        # Create a minimal FastAPI app for testing
        app = FastAPI()
        app.config = MagicMock()  # type: ignore[attr-defined]
        app.config.keycloak = mock_keycloak_config  # type: ignore[attr-defined]
        app.config.apolo = mock_apolo_config  # type: ignore[attr-defined]
        app.http = MagicMock()  # type: ignore[attr-defined]
        app.oauth = MagicMock(spec=Oauth)  # type: ignore[attr-defined]

        # Include the auth router directly (not root_router to avoid libmagic import)
        app.include_router(auth_router, prefix="/auth")

        # Create test client
        client = TestClient(app)

        # Mock the token validation
        with patch(
            "launchpad.auth.api.token_from_string",
            side_effect=mock_token_from_string,
        ):
            # Make the request
            response = client.post(
                "/auth/cookie",
                json={
                    "access_token": "mock-access-token-12345",
                },
            )

            # Verify response status
            assert response.status_code == 200

            # Verify cookie is set in the Set-Cookie header
            set_cookie_header = response.headers.get("set-cookie", "")
            assert COOKIE_TOKEN in set_cookie_header
            assert "mock-access-token-12345" in set_cookie_header
            assert ".example.com" in set_cookie_header
            assert "secure" in set_cookie_header.lower()
            assert "httponly" in set_cookie_header.lower()

    def test_set_auth_cookie_with_invalid_token(
        self,
    ) -> None:
        """Test that POST /auth/cookie rejects invalid tokens"""
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi import FastAPI
        from starlette.testclient import TestClient

        from launchpad.auth.api import auth_router
        from launchpad.auth.oauth import Oauth
        from launchpad.config import KeycloakConfig
        from launchpad.errors import Unauthorized

        # Create mock app config
        mock_keycloak_config = KeycloakConfig(
            url=URL("http://mock-keycloak.com"),
            realm="mock-realm",
            client_id="mock-client-id",
        )

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        # Create a minimal FastAPI app for testing
        app = FastAPI()
        app.config = MagicMock()  # type: ignore[attr-defined]
        app.config.keycloak = mock_keycloak_config  # type: ignore[attr-defined]
        app.config.apolo = mock_apolo_config  # type: ignore[attr-defined]
        app.http = MagicMock()  # type: ignore[attr-defined]
        app.oauth = MagicMock(spec=Oauth)  # type: ignore[attr-defined]

        # Include the auth router directly
        app.include_router(auth_router, prefix="/auth")

        # Create test client
        client = TestClient(app)

        # Mock the token validation to raise Unauthorized
        async def mock_token_from_string(**kwargs: dict[str, object]) -> None:
            raise Unauthorized("Invalid token")

        # Mock the token validation
        with patch(
            "launchpad.auth.api.token_from_string",
            side_effect=mock_token_from_string,
        ):
            # Make the request with invalid token
            response = client.post(
                "/auth/cookie",
                json={
                    "access_token": "invalid-token",
                },
            )

            # Verify response status is 401
            assert response.status_code == 401

    def test_set_auth_cookie_without_base_domain(
        self,
    ) -> None:
        """Test that POST /auth/cookie fails gracefully when base_domain is not set"""
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi import FastAPI
        from starlette.testclient import TestClient

        from launchpad.auth.api import auth_router
        from launchpad.auth.oauth import Oauth
        from launchpad.config import KeycloakConfig

        # Create mock app config
        mock_keycloak_config = KeycloakConfig(
            url=URL("http://mock-keycloak.com"),
            realm="mock-realm",
            client_id="mock-client-id",
        )

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = None  # No base domain

        # Create mock decoded token response
        mock_decoded_token: dict[str, object] = {
            "email": "test@example.com",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["user"]},
        }

        # Create mock JWT validation function
        async def mock_token_from_string(
            **kwargs: dict[str, object],
        ) -> dict[str, object]:
            return mock_decoded_token

        # Create a minimal FastAPI app for testing
        app = FastAPI()
        app.config = MagicMock()  # type: ignore[attr-defined]
        app.config.keycloak = mock_keycloak_config  # type: ignore[attr-defined]
        app.config.apolo = mock_apolo_config  # type: ignore[attr-defined]
        app.http = MagicMock()  # type: ignore[attr-defined]
        app.oauth = MagicMock(spec=Oauth)  # type: ignore[attr-defined]

        # Include the auth router directly
        app.include_router(auth_router, prefix="/auth")

        # Create test client
        client = TestClient(app)

        # Mock the token validation
        with patch(
            "launchpad.auth.api.token_from_string",
            side_effect=mock_token_from_string,
        ):
            # Make the request
            response = client.post(
                "/auth/cookie",
                json={
                    "access_token": "mock-access-token-12345",
                },
            )

            # Verify response status is 500
            assert response.status_code == 500


class TestCookieDeletion:
    """Tests for cookie deletion on logout"""

    def test_logout_deletes_token_cookie(self, oauth_instance: Oauth) -> None:
        """Test that logout deletes the launchpad-token cookie"""
        from starlette.responses import Response

        response = Response()

        oauth_instance.logout(response)

        # Response should have delete-cookie headers
        set_cookie_headers = response.headers.getlist("set-cookie")
        # Should have multiple headers (one for each cookie being deleted)
        assert len(set_cookie_headers) > 0
        # Find the header for launchpad-token
        token_cookie_header = next(
            (h for h in set_cookie_headers if COOKIE_TOKEN in h), None
        )
        assert token_cookie_header is not None

    def test_logout_deletes_code_verifier_cookie(self, oauth_instance: Oauth) -> None:
        """Test that logout deletes the code_verifier cookie"""
        from starlette.responses import Response

        response = Response()

        oauth_instance.logout(response)

        set_cookie_headers = response.headers.getlist("set-cookie")
        # Find the header for code_verifier
        code_verifier_header = next(
            (h for h in set_cookie_headers if COOKIE_CODE_VERIFIER in h), None
        )
        assert code_verifier_header is not None

    def test_logout_includes_secure_and_httponly(self, oauth_instance: Oauth) -> None:
        """Test that logout deletes cookies with secure and httponly flags"""
        from starlette.responses import Response

        response = Response()

        oauth_instance.logout(response)

        set_cookie_headers = response.headers.getlist("set-cookie")
        # Check that at least one header has the security flags
        assert any("secure" in h.lower() for h in set_cookie_headers)
        assert any("httponly" in h.lower() for h in set_cookie_headers)


class TestOAuthRedirectFlow:
    """Tests for cookie creation during OAuth redirect"""

    def test_redirect_sets_code_verifier_cookie(self, oauth_instance: Oauth) -> None:
        """Test that redirect sets the code_verifier cookie"""
        original_url = "https://app.example.com/dashboard"

        response = oauth_instance.redirect(original_url)

        assert isinstance(response, RedirectResponse)
        set_cookie_header = response.headers.get("set-cookie", "")
        assert COOKIE_CODE_VERIFIER in set_cookie_header
        assert "secure" in set_cookie_header.lower()
        assert "httponly" in set_cookie_header.lower()

    def test_redirect_cookie_domain_matches_config(self, oauth_instance: Oauth) -> None:
        """Test that redirect cookie domain matches configured domain"""
        original_url = "https://app.example.com/dashboard"

        response = oauth_instance.redirect(original_url)

        set_cookie_header = response.headers.get("set-cookie", "")
        assert ".example.com" in set_cookie_header
