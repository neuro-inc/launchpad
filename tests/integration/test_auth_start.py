"""Integration test for the `/auth/start` route using TestClient.

This test spins up the real FastAPI app (via the existing `app_client`
fixture), injects a mock `app.oauth` object and verifies that a GET to
`/auth/start` returns the redirect response produced by that mock.
"""

from unittest.mock import MagicMock

from starlette.responses import RedirectResponse


def test_auth_start_integration() -> None:
    """Create the app with a patched lifespan and sync_db, inject a fake
    oauth implementation and exercise the real HTTP route via TestClient.

    This avoids requiring Docker/testcontainers by not using the session
    scoped fixtures that start a Postgres container.
    """
    from contextlib import asynccontextmanager
    from pathlib import Path
    from typing import AsyncIterator
    from unittest.mock import patch

    from fastapi.testclient import TestClient
    from starlette.requests import Request
    from yarl import URL

    from launchpad.app_factory import create_app
    from launchpad.config import (
        ApoloConfig,
        AppsConfig,
        BrandingConfig,
        Config,
        KeycloakConfig,
        PostgresConfig,
    )

    # Minimal config suitable for tests — no real DB/docker needed because
    # we will patch out the lifespan that would use DB/testcontainers.
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

    # Fake oauth.start_auth to return RedirectResponse with a cookie
    def _fake_start(request: Request) -> RedirectResponse:
        resp = RedirectResponse(
            url="https://mock-keycloak.example/realms/mock-realm/protocol/openid-connect/auth"
        )
        resp.set_cookie(
            "code_verifier",
            "dummy-verifier",
            domain=".mock-cookie.com",
            secure=True,
            httponly=True,
        )
        return resp

    mock_oauth = MagicMock()
    mock_oauth.start_auth.side_effect = _fake_start

    # Provide a noop lifespan so app creation doesn't attempt DB migrations
    @asynccontextmanager
    async def _noop_lifespan(app: object) -> AsyncIterator[None]:
        yield

    with (
        patch("launchpad.app_factory.sync_db"),
        patch("launchpad.app_factory.lifespan", _noop_lifespan),
    ):
        app = create_app(cfg)
        app.oauth = mock_oauth

        with TestClient(app) as client:
            response = client.get("/auth/start", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert "mock-keycloak.example" in response.headers.get("location", "")
    assert "code_verifier" in response.headers.get("set-cookie", "")
