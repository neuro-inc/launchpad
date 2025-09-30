import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from launchpad.app import Launchpad
from launchpad.apps.models import InstalledApp
from launchpad.apps.registry.base import App
from launchpad.apps.service import AppService
from launchpad.config import Config
from launchpad.ext.apps_api import AppsApiClient


@pytest.fixture
def mock_apps_api_client() -> AsyncMock:
    apps_api = AsyncMock(spec=AppsApiClient)
    apps_api.get_outputs.return_value = {}
    return apps_api


@pytest.fixture
def mock_db_session_maker() -> MagicMock:
    # This fixture provides an AsyncMock for AsyncSession, but AppService expects app.db to be async_sessionmaker
    # So, we need to mock app.db to return an AsyncMock context manager when called.
    mock_session_maker = MagicMock()
    mock_session_maker.return_value.__aenter__.return_value = AsyncMock(
        spec=AsyncSession
    )
    mock_session_maker.return_value.__aexit__.return_value = None
    return mock_session_maker


@pytest.fixture
def mock_launchpad_app(
    mock_apps_api_client: AsyncMock, mock_db_session_maker: MagicMock
) -> MagicMock:
    app = MagicMock(spec=Launchpad)
    app.apps_api_client = mock_apps_api_client
    app.db = mock_db_session_maker
    app.config = MagicMock(spec=Config)
    app.config.instance_id = uuid.uuid4()
    return app


@pytest.fixture
def app_service(mock_launchpad_app: MagicMock) -> AppService:
    return AppService(app=mock_launchpad_app)


@pytest.fixture
def app_id() -> UUID:
    return uuid.uuid4()


async def test_app_service_install_app_success(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    mock_db_session_maker: MagicMock,
    app_id: UUID,
) -> None:
    mock_app_instance = MagicMock(spec=App)  # Corrected to spec=App
    mock_app_instance.config = MagicMock(spec=Config)
    mock_app_instance.config.instance_id = "INSTANCE_ID"
    mock_app_instance.to_apps_api_payload.return_value = {
        "name": "test-app",
        "chart": "test-chart",
    }
    mock_app_instance.name = "test-app-name"
    mock_app_instance.is_internal = False
    mock_app_instance.is_shared = False
    mock_app_instance.template_name = "test-template"
    mock_app_instance.template_version = "1.0.0"
    mock_app_instance.verbose_name = "Test App"
    mock_app_instance.description_short = "Short description"
    mock_app_instance.description_long = "Long description"
    mock_app_instance.logo = "http://example.com/logo.png"
    mock_app_instance.documentation_urls = []
    mock_app_instance.external_urls = []
    mock_app_instance.tags = []

    mock_apps_api_client.install_app.return_value = {
        "id": "123",
        "name": "test-app",
        "status": "installing",
    }

    # Mock the insert_app function
    with patch("launchpad.apps.service.insert_app", new=AsyncMock()) as mock_insert_app:
        mock_insert_app.return_value = InstalledApp(
            app_id=app_id,
            app_name="test-app",
            launchpad_app_name="test-app-name",
            is_internal=False,
            is_shared=False,
            user_id=None,
            url=None,
            template_name="test-template",
            template_version="1.0.0",
            verbose_name="Test App",
            description_short="Short description",
            description_long="Long description",
            logo="http://example.com/logo.png",
            documentation_urls=[],
            external_urls=[],
            tags=[],
        )

        result = await app_service.install(
            app=mock_app_instance
        )  # Pass the mocked app instance

        assert result.app_id == app_id
        assert result.app_name == "test-app"
        mock_apps_api_client.install_app.assert_called_once_with(
            payload={"name": "test-app", "chart": "test-chart"}
        )
        mock_insert_app.assert_called_once()


async def test_app_service_delete_app_success(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    mock_db_session_maker: MagicMock,
    app_id: UUID,
) -> None:
    mock_apps_api_client.delete_app.return_value = None

    # Mock the delete_app function
    with patch("launchpad.apps.service.delete_app", new=AsyncMock()) as mock_delete_app:
        await app_service.delete(app_id)

        mock_apps_api_client.delete_app.assert_called_once_with(app_id)
        mock_delete_app.assert_called_once_with(
            mock_db_session_maker.return_value.__aenter__.return_value, app_id
        )


async def test_app_service_delete_app_not_found(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    mock_db_session_maker: MagicMock,
    app_id: UUID,
) -> None:
    # Mock the delete_app function to raise an error if app not found
    with patch("launchpad.apps.service.delete_app", new=AsyncMock()) as mock_delete_app:
        mock_delete_app.side_effect = ValueError(
            "App not found"
        )  # Simulate delete_app raising error

        with pytest.raises(ValueError, match="App not found"):
            await app_service.delete(app_id)

        mock_apps_api_client.delete_app.assert_called_once_with(app_id)
        mock_delete_app.assert_called_once_with(
            mock_db_session_maker.return_value.__aenter__.return_value, app_id
        )
