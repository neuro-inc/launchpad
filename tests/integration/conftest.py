import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from yarl import URL

from launchpad.app_factory import create_app
from launchpad.auth.dependencies import (
    admin_role_required,
    auth_required,
)
from launchpad.auth.models import User
from launchpad.config import (
    ApoloConfig,
    AppsConfig,
    BrandingConfig,
    Config,
    KeycloakConfig,
    PostgresConfig,
    ServerConfig,
)
from launchpad.db.base import Base


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


@pytest.fixture(scope="session")
def setup_database(postgres_container: PostgresContainer) -> Iterator[str]:
    """Create database tables once for all tests (session-scoped)"""
    sync_dsn = postgres_container.get_connection_url(driver=None).replace(
        "postgresql://", "postgresql+psycopg2://"
    )
    sync_engine = create_engine(sync_dsn)

    # Create all tables once
    Base.metadata.create_all(sync_engine)

    yield sync_dsn

    # Cleanup: drop all tables at end of session
    Base.metadata.drop_all(sync_engine)
    sync_engine.dispose()


@pytest.fixture
def config(postgres_container: PostgresContainer, setup_database: str) -> Config:
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
    mock_branding_config = BrandingConfig(
        logo_url="https://example.com/logo.png",
        favicon_url="https://example.com/favicon.png",
        title="Test Title",
        background="12345",
    )

    mock_cfg = MagicMock(spec=Config)
    mock_cfg.keycloak = kc_config
    mock_cfg.apolo = apolo_config
    mock_cfg.apps = mock_apps_config
    mock_cfg.postgres = mock_pg_config
    mock_cfg.server = mock_server_config
    mock_cfg.skip_seed_templates = False
    mock_cfg.branding = mock_branding_config
    # Set a mock instance_id for output processing tests
    mock_cfg.instance_id = uuid4()
    return mock_cfg


@pytest.fixture
def mock_user() -> User:
    """Mock authenticated user for testing"""
    return User(
        id="test@example.com",
        email="test@example.com",
        name="Test User",
        groups=["admin"],
    )


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

    def install_app_side_effect(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(uuid4()),  # Generate unique UUID for each install
            "name": payload.get("template_name", "test-app"),
            "template_name": payload.get("template_name", "test-template"),
            "template_version": payload.get("template_version", "1.0.0"),
            "state": "queued",
        }

    # Mock get_inputs response
    def get_inputs_side_effect(app_id: UUID) -> dict[str, Any]:
        return {
            "displayName": "Test App Instance",
            "preset": {"name": "cpu-small"},
            "custom_config": {"key": "value"},
        }

    mock_client.get_by_id.side_effect = get_by_id_side_effect
    mock_client.get_template.side_effect = get_template_side_effect
    mock_client.install_app.side_effect = install_app_side_effect
    mock_client.get_inputs.side_effect = get_inputs_side_effect
    # Return proper structure for outputs with installed_apps list
    mock_client.get_outputs.return_value = {"installed_apps": {"app_list": []}}
    mock_client.update_outputs.return_value = None
    # Mock get_app_endpoints to return empty/None values (fallback behavior)
    mock_client.get_app_endpoints.return_value = (None, [])

    return mock_client


@pytest.fixture(scope="function")
def app_client(
    config: Config,
    mock_auth_dependency: Any,
    mock_apps_api_client: AsyncMock,
) -> Iterator[TestClient]:
    """
    Create test client with transactional database isolation.
    Each test runs in a transaction that is rolled back after completion.

    This approach creates tables once (session-scoped) and uses TRUNCATE
    to clean data between tests, which is much faster than CREATE/DROP.
    """
    from launchpad.db.dependencies import get_db

    # Patch sync_db to skip alembic migrations (tables already exist)
    with patch("launchpad.app_factory.sync_db"):
        # Patch AppsApiClient to return our mock
        with patch("launchpad.lifespan.AppsApiClient") as mock_api_client_class:
            mock_api_client_class.return_value = mock_apps_api_client

            # Create the app (uses real PostgreSQL from config)
            app = create_app(config)

            # Override auth dependencies
            app.dependency_overrides[auth_required] = mock_auth_dependency
            app.dependency_overrides[admin_role_required] = mock_auth_dependency

            with TestClient(app) as client:
                yield client

            # Cleanup: truncate all tables for next test
            # This is much faster than DROP/CREATE and provides isolation
            sync_dsn = config.postgres.dsn.replace("+asyncpg", "+psycopg2")
            sync_engine = create_engine(sync_dsn)
            with sync_engine.connect() as connection:
                # Use a transaction to truncate all tables
                trans = connection.begin()
                try:
                    for table in reversed(Base.metadata.sorted_tables):
                        connection.execute(table.delete())
                    trans.commit()
                except Exception:
                    trans.rollback()
                    raise
            sync_engine.dispose()
