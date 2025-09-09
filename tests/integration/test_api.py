from collections.abc import AsyncIterator
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient  # Import TestClient
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
)
from yarl import URL

from launchpad.app_factory import create_app
from launchpad.config import (
    Config,
    KeycloakConfig,
    ApoloConfig,
    AppsConfig,
    PostgresConfig,
    ServerConfig,
)


@pytest.fixture(scope="module")
def config() -> Config:
    kc_config = KeycloakConfig(
        url=URL("http://mock-keycloak.com"), realm="mock-realm", client_id="frontend"
    )
    apolo_config = ApoloConfig(
        cluster="test-cluster",
        org_name="test-org",
        project_name="test-project",
        apps_api_url="http://mock-apps-api.com",
        token="mock-token",
        self_domain="http://mock-self.com",
        base_domain="http://mock-base.com",
        auth_middleware_name="test-middleware",
    )
    mock_apps_config = AppsConfig(vllm={}, postgres={}, embeddings={})
    # Corrected DSN with a valid port number
    mock_pg_config = PostgresConfig(dsn="postgresql+asyncpg://user:pass@host:5432/db")
    mock_server_config = ServerConfig()

    mock_cfg = MagicMock(spec=Config)
    mock_cfg.keycloak = kc_config
    mock_cfg.apolo = apolo_config
    mock_cfg.apps = mock_apps_config
    mock_cfg.postgres = mock_pg_config
    mock_cfg.server = mock_server_config
    return mock_cfg


@pytest.fixture(scope="module")
async def app_client(config: Config) -> AsyncIterator[TestClient]:
    with patch("launchpad.app_factory.sync_db"):
        with patch(
            "launchpad.db.lifespan.create_async_engine",
            new=AsyncMock(spec=create_async_engine),
        ) as mock_create_engine:
            mock_engine_instance = MagicMock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine_instance

            app = create_app(config)
            with TestClient(app) as client:
                yield client


async def test_ping_endpoint(app_client: TestClient) -> None:
    response = app_client.get("/ping")
    assert response.status_code == 200
    assert response.text == "Pong"


async def test_config_endpoint(app_client: TestClient, config: Config) -> None:
    response = app_client.get("/config")
    assert response.status_code == 200
    assert response.json() == {
        "keycloak": {
            "url": str(config.keycloak.url),
            "realm": config.keycloak.realm,
        },
    }
