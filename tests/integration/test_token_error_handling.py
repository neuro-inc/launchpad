"""
Tests for error handling improvements in POST /token endpoint.
Verifies that missing/empty access tokens and configuration errors are caught properly.
"""

from typing import Any, Coroutine, cast
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestTokenErrorHandling:
    """Tests for error handling in POST /token endpoint"""

    def test_post_token_missing_access_token_raises_error(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that missing access_token in Keycloak response raises HTTPException"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            # Missing access_token key
            response.json = AsyncMock(
                return_value={
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

        # Should fail with 502 Bad Gateway
        assert response.status_code == 502
        assert "Invalid authentication service response" in response.json()["detail"]

    def test_post_token_empty_access_token_raises_error(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that empty access_token in Keycloak response raises HTTPException"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            # Empty access_token
            response.json = AsyncMock(
                return_value={
                    "access_token": "",
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

        # Should fail with 502 Bad Gateway
        assert response.status_code == 502
        assert "Invalid authentication service response" in response.json()["detail"]

    def test_post_token_null_access_token_raises_error(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that null access_token in Keycloak response raises HTTPException"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            # Null access_token
            response.json = AsyncMock(
                return_value={
                    "access_token": None,
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

        # Should fail with 502 Bad Gateway
        assert response.status_code == 502
        assert "Invalid authentication service response" in response.json()["detail"]

    def test_post_token_missing_config_raises_error(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that missing config raises proper HTTPException (500)"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "valid-jwt-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        def mock_config_error(*args: Any, **kwargs: Any) -> None:
            raise AttributeError("config.apolo.base_domain missing")

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            # Mock the config to raise an error
            app = cast(Any, app_client).app
            with patch.object(
                type(app.config.apolo),
                "base_domain",
                new_callable=lambda: property(
                    lambda self: (_ for _ in ()).throw(AttributeError("missing"))
                ),
            ):
                # Actually, let's mock it differently - patch the whole config access
                original_config = app.config

                class BadConfig:
                    @property
                    def apolo(self) -> Any:
                        raise AttributeError("config.apolo missing")

                app.config = BadConfig()

                try:
                    response = app_client.post(
                        "/token",
                        json={"username": "testuser", "password": "testpass"},
                    )

                    # Should fail with 500 Server Error
                    assert response.status_code == 500
                    assert "Server configuration error" in response.json()["detail"]
                finally:
                    app.config = original_config

    def test_post_token_valid_token_no_cookie_without_domain(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that valid token is returned but cookie not set when base_domain is empty"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "valid-jwt-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            # Mock empty base_domain
            app = cast(Any, app_client).app
            original_base_domain = app.config.apolo.base_domain
            app.config.apolo.base_domain = ""

            try:
                response = app_client.post(
                    "/token",
                    json={"username": "testuser", "password": "testpass"},
                )

                # Should succeed
                assert response.status_code == 200
                data = response.json()
                assert data["access_token"] == "valid-jwt-token"

                # Should NOT set cookie when base_domain is empty
                if "set-cookie" in response.headers:
                    # If set-cookie header exists, it shouldn't contain launchpad-token
                    assert "launchpad-token" not in response.headers["set-cookie"]
            finally:
                app.config.apolo.base_domain = original_base_domain


class TestAccessTokenValidation:
    """Tests specifically for access_token validation logic"""

    def test_access_token_extraction_success(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test successful extraction of valid access_token"""
        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"

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
        data = response.json()
        assert data["access_token"] == test_token


class TestConfigErrorHandling:
    """Tests for specific configuration error handling"""

    def test_config_attribute_error_caught(
        self,
        app_client: TestClient,
        monkeypatch: Any,
    ) -> None:
        """Test that AttributeError from config access is caught properly"""

        async def mock_post(
            *args: Any, **kwargs: Any
        ) -> Coroutine[Any, Any, MagicMock]:
            response = MagicMock()
            response.status = 200
            response.json = AsyncMock(
                return_value={
                    "access_token": "valid-token",
                    "token_type": "Bearer",
                }
            )
            response.raise_for_status = MagicMock()
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=False)
            return response

        with patch("aiohttp.ClientSession.post", side_effect=mock_post):
            # Save original
            app = cast(Any, app_client).app
            original_config = app.config

            try:
                # Create a config that raises AttributeError
                class BrokenConfig:
                    @property
                    def apolo(self) -> Any:
                        raise AttributeError("apolo config missing")

                app.config = BrokenConfig()

                response = app_client.post(
                    "/token",
                    json={"username": "testuser", "password": "testpass"},
                )

                # Should return 500 with specific error message
                assert response.status_code == 500
                assert "Server configuration error" in response.json()["detail"]
            finally:
                app.config = original_config
