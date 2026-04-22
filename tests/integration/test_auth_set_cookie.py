"""Integration tests for the `/auth/set-cookie` endpoint."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch

from aiohttp import ClientSession
from fastapi.testclient import TestClient
from yarl import URL

from launchpad.app_factory import create_app
from launchpad.auth.oauth import Oauth
from launchpad.config import (
    ApoloConfig,
    AppsConfig,
    BrandingConfig,
    Config,
    KeycloakConfig,
    PostgresConfig,
)


def _make_config() -> Config:
    return Config(
        postgres=PostgresConfig(dsn="sqlite+aiosqlite:///:memory:"),
        keycloak=KeycloakConfig(
            url=URL("http://mock-keycloak.test"),
            realm="mock-realm",
            client_id="frontend",
        ),
        apolo=ApoloConfig(
            cluster="test",
            org_name="org",
            project_name="proj",
            apps_api_url="http://mock-apps",
            token="tok",
            self_domain="mock-launchpad.com",
            web_app_domain="mock-web.com",
            base_domain="mock-base.com",
            auth_middleware_name="middleware",
        ),
        branding=BrandingConfig(
            title="t", background="b", branding_dir=Path(__file__).parent
        ),
        apps=AppsConfig(vllm={}, postgres={}, embeddings={}),
    )


def _make_app() -> tuple[TestClient, AsyncMock]:
    cfg = _make_config()
    mock_http = AsyncMock(spec=ClientSession)
    oauth_instance = Oauth(
        http=mock_http,
        keycloak_config=cfg.keycloak,
        cookie_domain=cfg.apolo.base_domain,
        launchpad_domain=cfg.apolo.self_domain,
    )

    @asynccontextmanager
    async def _noop_lifespan(app: object) -> AsyncIterator[None]:
        yield

    with (
        patch("launchpad.app_factory.sync_db"),
        patch("launchpad.app_factory.lifespan", _noop_lifespan),
    ):
        app = create_app(cfg)
        # attach the mocked http client so code that accesses `request.app.http`
        # in the auth handlers uses our AsyncMock instead of raising an
        # AttributeError during tests
        app.http = mock_http
        app.oauth = oauth_instance
        client = TestClient(app)

    return client, mock_http


def test_set_cookie_sets_launchpad_token_cookie() -> None:
    client, _ = _make_app()

    with patch("launchpad.auth.api.token_from_string", new=AsyncMock(return_value={})):
        response = client.post(
            "/auth/set-cookie",
            headers={"Authorization": "Bearer mock-access-token"},
        )

    assert response.status_code == 200
    assert "launchpad-token=mock-access-token" in response.headers.get("set-cookie", "")


def test_set_cookie_rejects_missing_authorization_header() -> None:
    client, _ = _make_app()

    response = client.post("/auth/set-cookie")

    assert response.status_code == 401
