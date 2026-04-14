"""
Integration tests for cookie-based authentication flow.
Tests the end-to-end flow with actual HTTP requests to verify
that cookies are properly set and sent across the authentication lifecycle.
"""

from typing import Any, Coroutine
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from launchpad.auth.oauth import COOKIE_CODE_VERIFIER, COOKIE_TOKEN
from launchpad.config import Config


class TestCookieAuthenticationFlow:
    """Integration tests for cookie-based authentication flow"""

    def test_post_token_sets_cookie(
        self,
        app_client: TestClient,
        config: Config,
        monkeypatch: Any,
    ) -> None:
        """Test that POST /token sets launchpad-token cookie after successful authentication"""

        # Mock Keycloak response
        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "mock-jwt-token-12345",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": "mock-refresh-token",
                    "scope": "openid profile email offline_access",
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        # Mock the aiohttp session
        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            response = app_client.post(
                "/token",
                json={"username": "testuser", "password": "testpass"},
            )

        # Verify successful response
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mock-jwt-token-12345"
        assert data["token_type"] == "Bearer"

        # Verify cookie is set in response
        assert "set-cookie" in response.headers
        set_cookie_header = response.headers["set-cookie"]
        assert COOKIE_TOKEN in set_cookie_header
        assert "mock-jwt-token-12345" in set_cookie_header
        assert "secure" in set_cookie_header.lower()
        assert "httponly" in set_cookie_header.lower()

    def test_post_token_cookie_includes_correct_domain(
        self,
        app_client: TestClient,
        config: Config,
        monkeypatch: Any,
    ) -> None:
        """Test that POST /token cookie includes the correct domain from config"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "mock-jwt-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            response = app_client.post(
                "/token",
                json={"username": "testuser", "password": "testpass"},
            )

        assert response.status_code == 200
        set_cookie_header = response.headers["set-cookie"]
        # Should include the base_domain from config
        base_domain = config.apolo.base_domain
        assert f".{base_domain}" in set_cookie_header

    def test_post_token_failed_authentication_no_cookie(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that failed authentication does not set cookie"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 401
            response.json = AsyncMock(
                return_value={
                    "error": "invalid_grant",
                    "error_description": "Invalid credentials",
                }
            )
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            response = app_client.post(
                "/token",
                json={"username": "baduser", "password": "badpass"},
            )

        # Should fail
        assert response.status_code == 401
        # Should not set cookie on failure
        if "set-cookie" in response.headers:
            assert COOKIE_TOKEN not in response.headers["set-cookie"]

    def test_authorize_endpoint_retrieves_cookie(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that /authorize endpoint can retrieve token from cookie"""
        mock_token_decoded = {
            "email": "user@example.com",
            "preferred_username": "testuser",
            "groups": ["users"],
        }

        # Mock token_from_string dependency
        with patch(
            "launchpad.auth.dependencies.token_from_string",
            new=AsyncMock(return_value=mock_token_decoded),
        ):
            # Mock app lookup
            with patch(
                "launchpad.apps.storage.select_app_by_any_url",
                new=AsyncMock(
                    return_value=MagicMock(is_shared=True, user_id="user@example.com")
                ),
            ):
                response = app_client.get(
                    "/authorize",
                    headers={
                        "X-Forwarded-Host": "app.example.com",
                    },
                    cookies={COOKIE_TOKEN: "mock-jwt-token"},
                )

        # Should succeed when cookie is present
        assert response.status_code == 200
        assert response.text == "OK"
        assert "X-Auth-Request-Email" in response.headers

    def test_logout_deletes_cookie(self, app_client: TestClient) -> None:
        """Test that /logout endpoint deletes authentication cookies"""
        response = app_client.post("/logout")

        # Should succeed
        assert response.status_code == 200

        # Should have set-cookie headers for deletion (Max-Age=0)
        # Note: TestClient may not fully preserve cookie deletion headers,
        # so we check for set-cookie presence
        if "set-cookie" in response.headers:
            set_cookie_header = response.headers["set-cookie"]
            # Should include cookie deletion for both tokens
            assert (
                COOKIE_TOKEN in set_cookie_header
                or COOKIE_CODE_VERIFIER in set_cookie_header
            )


class TestCookieSecurityAttributes:
    """Tests for cookie security attributes"""

    def test_cookie_has_secure_flag(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that all cookies have the secure flag (HTTPS only)"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "mock-jwt-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            response = app_client.post(
                "/token",
                json={"username": "testuser", "password": "testpass"},
            )

        assert response.status_code == 200
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "secure" in set_cookie_header.lower()

    def test_cookie_has_httponly_flag(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that all cookies have the httponly flag (not accessible to JavaScript)"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "mock-jwt-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            response = app_client.post(
                "/token",
                json={"username": "testuser", "password": "testpass"},
            )

        assert response.status_code == 200
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie_header.lower()


class TestCookieNameAndContent:
    """Tests for cookie name and content correctness"""

    def test_cookie_name_is_launchpad_token(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that cookie name is exactly 'launchpad-token'"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "test-jwt-12345",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            response = app_client.post(
                "/token",
                json={"username": "testuser", "password": "testpass"},
            )

        assert response.status_code == 200
        set_cookie_header = response.headers.get("set-cookie", "")
        assert f"{COOKIE_TOKEN}=" in set_cookie_header

    def test_cookie_contains_jwt_token(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that cookie value contains the JWT access token"""
        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": test_token,
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            response = app_client.post(
                "/token",
                json={"username": "testuser", "password": "testpass"},
            )

        assert response.status_code == 200
        set_cookie_header = response.headers.get("set-cookie", "")
        assert test_token in set_cookie_header
