"""Integration test for the `/auth/callback` route using TestClient.

The test creates a real FastAPI app (with a noop lifespan to avoid DB
and external services), injects a real `Oauth` instance whose HTTP client
is mocked, and performs a GET to `/auth/callback` to assert that the
access token cookie is set and the user is redirected to the original
URL encoded in the state parameter.
"""

import base64
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

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


def test_auth_callback_sets_cookie_and_redirects() -> None:
    # Prepare a minimal config and noop lifespan so app creation is fast
    cfg = Config(
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
            web_app_domain="mock-web",
            base_domain="mock-base",
            auth_middleware_name="middleware",
        ),
        branding=BrandingConfig(
            title="t", background="b", branding_dir=Path(__file__).parent
        ),
        apps=AppsConfig(vllm={}, postgres={}, embeddings={}),
    )

    # Mocked aiohttp session that returns a response with an access_token
    mock_http = AsyncMock(spec=ClientSession)
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    async def _json() -> dict[str, str]:
        return {"access_token": "mock-access-token"}

    mock_response.json = _json
    mock_http.post.return_value.__aenter__.return_value = mock_response

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
        # Inject our prepared oauth instance that uses the mocked http client
        app.oauth = oauth_instance

        # Prepare original URL/state and code_verifier cookie
        original_url = "https://original.example/path"
        state = base64.urlsafe_b64encode(original_url.encode()).decode()

        with TestClient(app) as client:
            # set cookie on the client so the request carries it
            client.cookies.set("code_verifier", "mock-code-verifier")
            response = client.get(
                f"/auth/callback?code=mock-code&state={state}", follow_redirects=False
            )

    assert response.status_code in (302, 307)
    assert response.headers.get("location") == original_url
    assert "launchpad-token" in response.headers.get("set-cookie", "")
