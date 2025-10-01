from collections.abc import AsyncIterator, Iterator
from typing import Any
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import UUID
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from testcontainers.postgres import PostgresContainer
from yarl import URL

from launchpad.app_factory import create_app
from launchpad.auth.models import User
from launchpad.config import (
    Config,
    KeycloakConfig,
    ApoloConfig,
    AppsConfig,
    PostgresConfig,
    ServerConfig,
)

# Suppress verbose logging from libraries during tests
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("testcontainers").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def postgres_container() -> Any:
    """Start a PostgreSQL container for integration tests"""
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture
def config(postgres_container: PostgresContainer) -> Config:
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

    # Use the real PostgreSQL connection string with asyncpg driver
    pg_dsn = postgres_container.get_connection_url(driver=None).replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    mock_pg_config = PostgresConfig(dsn=pg_dsn)
    mock_server_config = ServerConfig()

    mock_cfg = MagicMock(spec=Config)
    mock_cfg.keycloak = kc_config
    mock_cfg.apolo = apolo_config
    mock_cfg.apps = mock_apps_config
    mock_cfg.postgres = mock_pg_config
    mock_cfg.server = mock_server_config
    return mock_cfg


@pytest.fixture
def mock_user() -> User:
    """Mock authenticated user for testing"""
    return User(id="test@example.com", email="test@example.com", name="Test User")


@pytest.fixture
def mock_auth_dependency(mock_user: User) -> Any:
    """Mock authentication dependency"""

    async def mock_auth_required() -> User:
        return mock_user

    return mock_auth_required


@pytest.fixture
def mock_apps_api_client() -> AsyncMock:
    """Mock Apps API client with common responses"""
    mock_client = AsyncMock()

    # Mock get_by_id response
    def get_by_id_side_effect(app_id: UUID) -> dict[str, Any]:
        return {
            "id": str(app_id),
            "name": f"app-{app_id}",
            "template_name": "test-template",
            "template_version": "1.0.0",
            "display_name": "Test App Instance",
            "state": "healthy",
        }

    # Mock get_template response
    def get_template_side_effect(
        template_name: str, template_version: str
    ) -> dict[str, Any]:
        return {
            "name": template_name,
            "version": template_version,
            "title": f"{template_name} v{template_version}",
            "description": "Long description from Apps API",
            "short_description": "Short description from Apps API",
            "logo": "https://example.com/logo.png",
            "tags": ["ml", "inference"],
            "documentation_urls": [{"text": "Docs", "url": "https://docs.example.com"}],
            "external_urls": [{"text": "GitHub", "url": "https://github.com/example"}],
        }

    # Mock install_app response
    from uuid import uuid4

    def install_app_side_effect(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(uuid4()),  # Generate unique UUID for each install
            "name": payload.get("template_name", "test-app"),
            "template_name": payload.get("template_name", "test-template"),
            "template_version": payload.get("template_version", "1.0.0"),
            "state": "queued",
        }

    mock_client.get_by_id.side_effect = get_by_id_side_effect
    mock_client.get_template.side_effect = get_template_side_effect
    mock_client.install_app.side_effect = install_app_side_effect
    mock_client.get_outputs.return_value = {}
    mock_client.update_outputs.return_value = None

    return mock_client


@pytest.fixture(scope="function")
def app_client(
    config: Config, mock_auth_dependency: Any, mock_apps_api_client: AsyncMock
) -> Iterator[TestClient]:
    """Create test client with mocked dependencies and real PostgreSQL"""
    # Create tables before app starts using a temporary engine
    from launchpad.db.base import Base
    from sqlalchemy import create_engine

    # Create sync engine for table setup/teardown
    sync_dsn = config.postgres.dsn.replace("+asyncpg", "+psycopg2")
    sync_engine = create_engine(sync_dsn)
    Base.metadata.create_all(sync_engine)

    try:
        # Patch sync_db to skip alembic migrations (tables already exist)
        with patch("launchpad.app_factory.sync_db"):
            # Patch AppsApiClient to return our mock
            with patch("launchpad.lifespan.AppsApiClient") as mock_api_client_class:
                mock_api_client_class.return_value = mock_apps_api_client

                # Create the app (uses real PostgreSQL from config)
                app = create_app(config)

                # Override auth dependency
                from launchpad.auth.dependencies import auth_required

                app.dependency_overrides[auth_required] = mock_auth_dependency

                with TestClient(app) as client:
                    yield client
    finally:
        # Cleanup - drop all tables
        Base.metadata.drop_all(sync_engine)
        sync_engine.dispose()
