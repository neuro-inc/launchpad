"""
Unit tests for the TokenCookieMiddleware.
These tests verify that the launchpad-token cookie is automatically set
when a valid Bearer token is present in the Authorization header.
"""

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient
from yarl import URL

from launchpad.app import Launchpad
from launchpad.auth.middleware import TokenCookieMiddleware
from launchpad.auth.oauth import COOKIE_TOKEN
from launchpad.config import KeycloakConfig


@pytest.fixture
def mock_keycloak_config() -> KeycloakConfig:
    """Mock Keycloak configuration"""
    return KeycloakConfig(
        url=URL("http://mock-keycloak.com"),
        realm="mock-realm",
        client_id="mock-client-id",
    )


class TestTokenCookieMiddleware:
    """Tests for TokenCookieMiddleware"""

    def test_middleware_sets_cookie_with_valid_bearer_token(
        self,
        mock_keycloak_config: KeycloakConfig,
    ) -> None:
        """Test that middleware sets cookie when valid Bearer token is present"""
        from unittest.mock import patch

        from launchpad.auth.api import auth_router
        from launchpad.auth.oauth import Oauth

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        mock_decoded_token: dict[str, object] = {
            "email": "test@example.com",
            "preferred_username": "testuser",
        }

        async def mock_token_from_string(
            **kwargs: dict[str, object],
        ) -> dict[str, object]:
            return mock_decoded_token

        app: Launchpad = Launchpad()
        app.config = MagicMock()
        app.config.keycloak = mock_keycloak_config
        app.config.apolo = mock_apolo_config
        app.http = MagicMock()
        app.oauth = MagicMock(spec=Oauth)

        app.include_router(auth_router, prefix="/auth")
        app.add_middleware(TokenCookieMiddleware)

        client = TestClient(app)

        with patch(
            "launchpad.auth.middleware.token_from_string",
            side_effect=mock_token_from_string,
        ):
            response = client.get(
                "/api/v1/apps",
                headers={"Authorization": "Bearer valid-token-123"},
            )

            # Cookie should be set in the response
            set_cookie_header = response.headers.get("set-cookie", "")
            assert COOKIE_TOKEN in set_cookie_header
            assert "valid-token-123" in set_cookie_header
            assert ".example.com" in set_cookie_header
            assert "secure" in set_cookie_header.lower()
            assert "httponly" in set_cookie_header.lower()

    def test_middleware_skips_auth_endpoints(
        self,
        mock_keycloak_config: KeycloakConfig,
    ) -> None:
        """Test that middleware doesn't set cookie on auth endpoints"""
        from unittest.mock import patch

        from starlette.responses import Response

        from launchpad.auth.oauth import Oauth

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        app: Launchpad = Launchpad()
        app.config = MagicMock()
        app.config.keycloak = mock_keycloak_config
        app.config.apolo = mock_apolo_config
        app.http = MagicMock()
        app.oauth = MagicMock(spec=Oauth)

        # Add a simple auth-like endpoint
        @app.get("/auth/test")
        def auth_test() -> Response:
            return Response("OK")

        app.add_middleware(TokenCookieMiddleware)

        client = TestClient(app)

        # Mock token validation to ensure it's NOT called for auth endpoints
        with patch(
            "launchpad.auth.middleware.token_from_string",
        ) as mock_validate:
            response = client.get(
                "/auth/test",
                headers={"Authorization": "Bearer valid-token-123"},
            )

            # Token validation should NOT be called for auth endpoints
            mock_validate.assert_not_called()

            # Cookie should NOT be set by middleware (auth endpoints handle it themselves)
            set_cookie_header = response.headers.get("set-cookie", "")
            # The cookie should not be set by middleware for /auth/ paths
            assert COOKIE_TOKEN not in set_cookie_header

    def test_middleware_skips_when_cookie_already_exists(
        self,
        mock_keycloak_config: KeycloakConfig,
    ) -> None:
        """Test that middleware doesn't override existing cookie"""
        from unittest.mock import patch

        from starlette.responses import Response

        from launchpad.auth.oauth import Oauth

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        app: Launchpad = Launchpad()
        app.config = MagicMock()
        app.config.keycloak = mock_keycloak_config
        app.config.apolo = mock_apolo_config
        app.http = MagicMock()
        app.oauth = MagicMock(spec=Oauth)

        # Add a simple endpoint
        @app.get("/api/test")
        def api_test() -> Response:
            return Response("OK")

        app.add_middleware(TokenCookieMiddleware)

        # Create client with existing cookie
        client = TestClient(app, cookies={COOKIE_TOKEN: "existing-token"})

        with patch(
            "launchpad.auth.middleware.token_from_string",
        ) as mock_validate:
            response = client.get(
                "/api/test",
                headers={"Authorization": "Bearer new-token"},
            )

            # Token validation should NOT be called when cookie already exists
            mock_validate.assert_not_called()

    def test_middleware_ignores_missing_auth_header(
        self,
        mock_keycloak_config: KeycloakConfig,
    ) -> None:
        """Test that middleware does nothing when no Authorization header is present"""
        from unittest.mock import patch

        from launchpad.auth.api import auth_router
        from launchpad.auth.oauth import Oauth

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        app: Launchpad = Launchpad()
        app.config = MagicMock()
        app.config.keycloak = mock_keycloak_config
        app.config.apolo = mock_apolo_config
        app.http = MagicMock()
        app.oauth = MagicMock(spec=Oauth)

        app.include_router(auth_router, prefix="/auth")
        app.add_middleware(TokenCookieMiddleware)

        client = TestClient(app)

        with patch(
            "launchpad.auth.middleware.token_from_string",
        ) as mock_validate:
            response = client.get("/api/v1/apps")

            # Token validation should NOT be called without Authorization header
            mock_validate.assert_not_called()

            # Cookie should NOT be set
            set_cookie_header = response.headers.get("set-cookie", "")
            assert COOKIE_TOKEN not in set_cookie_header

    def test_middleware_ignores_non_bearer_tokens(
        self,
        mock_keycloak_config: KeycloakConfig,
    ) -> None:
        """Test that middleware ignores non-Bearer Authorization tokens"""
        from unittest.mock import patch

        from launchpad.auth.api import auth_router
        from launchpad.auth.oauth import Oauth

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        app: Launchpad = Launchpad()
        app.config = MagicMock()
        app.config.keycloak = mock_keycloak_config
        app.config.apolo = mock_apolo_config
        app.http = MagicMock()
        app.oauth = MagicMock(spec=Oauth)

        app.include_router(auth_router, prefix="/auth")
        app.add_middleware(TokenCookieMiddleware)

        client = TestClient(app)

        with patch(
            "launchpad.auth.middleware.token_from_string",
        ) as mock_validate:
            response = client.get(
                "/api/v1/apps",
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
            )

            # Token validation should NOT be called for non-Bearer tokens
            mock_validate.assert_not_called()

    def test_middleware_handles_invalid_token_gracefully(
        self,
        mock_keycloak_config: KeycloakConfig,
    ) -> None:
        """Test that middleware doesn't fail request when token validation fails"""
        from unittest.mock import patch

        from starlette.responses import Response

        from launchpad.auth.oauth import Oauth
        from launchpad.errors import Unauthorized

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        async def mock_token_from_string_invalid(
            **kwargs: dict[str, object],
        ) -> dict[str, object]:
            raise Unauthorized("Invalid token")

        app: Launchpad = Launchpad()
        app.config = MagicMock()
        app.config.keycloak = mock_keycloak_config
        app.config.apolo = mock_apolo_config
        app.http = MagicMock()
        app.oauth = MagicMock(spec=Oauth)

        @app.get("/ping")
        def ping() -> Response:
            return Response("Pong")

        app.add_middleware(TokenCookieMiddleware)

        client = TestClient(app)

        with patch(
            "launchpad.auth.middleware.token_from_string",
            side_effect=mock_token_from_string_invalid,
        ):
            # Request should still succeed even if token validation fails
            response = client.get(
                "/ping",
                headers={"Authorization": "Bearer invalid-token"},
            )

            # Request should complete successfully
            assert response.status_code == 200

            # Cookie should NOT be set for invalid token
            set_cookie_header = response.headers.get("set-cookie", "")
            assert COOKIE_TOKEN not in set_cookie_header

    def test_middleware_skips_openapi_endpoints(
        self,
        mock_keycloak_config: KeycloakConfig,
    ) -> None:
        """Test that middleware skips OpenAPI documentation endpoints"""
        from unittest.mock import patch

        from starlette.responses import Response

        from launchpad.auth.oauth import Oauth

        mock_apolo_config = MagicMock()
        mock_apolo_config.base_domain = "example.com"

        app: Launchpad = Launchpad()
        app.config = MagicMock()
        app.config.keycloak = mock_keycloak_config
        app.config.apolo = mock_apolo_config
        app.http = MagicMock()
        app.oauth = MagicMock(spec=Oauth)

        @app.get("/openapi/test")
        def openapi_test() -> Response:
            return Response("OK")

        app.add_middleware(TokenCookieMiddleware)

        client = TestClient(app)

        with patch(
            "launchpad.auth.middleware.token_from_string",
        ) as mock_validate:
            response = client.get(
                "/openapi/test",
                headers={"Authorization": "Bearer valid-token-123"},
            )

            # Token validation should NOT be called for OpenAPI endpoints
            mock_validate.assert_not_called()
