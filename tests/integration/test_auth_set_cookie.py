from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncContextManager, AsyncIterator, Callable, Generator
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession
from fastapi import FastAPI
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


@pytest.fixture
def mock_config() -> Config:
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
            self_domain="https://mock-launchpad.com",
            web_app_domain="https://mock-launchpad.com",
            base_domain="mock-base.com",
            auth_middleware_name="middleware",
        ),
        branding=BrandingConfig(
            title="t",
            background="b",
            branding_dir=Path(__file__).parent,
        ),
        apps=AppsConfig(vllm={}, postgres={}, embeddings={}),
    )


@pytest.fixture
def mock_http() -> AsyncMock:
    return AsyncMock(spec=ClientSession)


@pytest.fixture
def oauth(mock_http: AsyncMock, mock_config: Config) -> Oauth:
    return Oauth(
        http=mock_http,
        keycloak_config=mock_config.keycloak,
        cookie_domain=mock_config.apolo.base_domain,
        launchpad_domain=mock_config.apolo.self_domain,
    )


@pytest.fixture
def noop_lifespan() -> Callable[[object], AsyncContextManager[None]]:
    @asynccontextmanager
    async def _lifespan(app: object) -> AsyncIterator[None]:
        yield

    return _lifespan


@pytest.fixture
def app(
    mock_config: Config,
    mock_http: AsyncMock,
    oauth: Oauth,
    noop_lifespan: Callable[[object], AsyncContextManager[None]],
) -> Generator[FastAPI, None, None]:
    with (
        patch("launchpad.app_factory.sync_db"),
        patch("launchpad.app_factory.lifespan", noop_lifespan),
    ):
        app = create_app(mock_config)
        app.config = mock_config
        app.http = mock_http
        app.oauth = oauth
        yield app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
