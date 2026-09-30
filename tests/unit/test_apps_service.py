import asyncio
import uuid
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from launchpad.app import Launchpad
from launchpad.apps.exceptions import AppTemplateNameConflict
from launchpad.apps.models import InstalledApp
from launchpad.apps.registry.base import App
from launchpad.apps.service import AppService
from launchpad.config import Config
from launchpad.ext.apps_api import AppsApiClient, NotFound as AppsApiNotFound
from launchpad.ext.launchpad_api import LaunchpadAdminApi


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
    app.http = AsyncMock()
    app.apolo_client = MagicMock()
    app.apps_api_client = mock_apps_api_client
    app.app_configurator = AsyncMock()
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
    mock_app_instance.user_id = None

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
            external_url_list=[],
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
        await app_service.delete(app_id, uninstall=True)

        mock_apps_api_client.delete_app.assert_called_once_with(app_id)
        mock_delete_app.assert_called_once_with(
            mock_db_session_maker.return_value.__aenter__.return_value, app_id
        )


async def test_app_service_delete_app_no_uninstall_success(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    mock_db_session_maker: MagicMock,
    app_id: UUID,
) -> None:
    mock_apps_api_client.delete_app.return_value = None

    # Mock the delete_app function
    with patch("launchpad.apps.service.delete_app", new=AsyncMock()) as mock_delete_app:
        await app_service.delete(app_id)

        mock_apps_api_client.delete_app.assert_not_called()
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
            await app_service.delete(app_id, uninstall=True)

        mock_apps_api_client.delete_app.assert_called_once_with(app_id)
        mock_delete_app.assert_called_once_with(
            mock_db_session_maker.return_value.__aenter__.return_value, app_id
        )


async def test_delete_app_from_previous_launchpad_falls_back_to_instance_delete(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    app_id: UUID,
) -> None:
    previous_launchpad_id = uuid.uuid4()
    mock_apps_api_client.cluster = "test-cluster"
    mock_apps_api_client.org_name = "test-org"
    mock_apps_api_client.project_name = "test-project"
    mock_apps_api_client.get_outputs.return_value = {"admin_api": {}, "admin_user": {}}

    previous_launchpad_admin = AsyncMock(spec=LaunchpadAdminApi)
    previous_launchpad_admin.delete_app_template_by_app_id.return_value = False

    with patch(
        "launchpad.apps.service.LaunchpadAdminApi.from_outputs",
        new=AsyncMock(return_value=previous_launchpad_admin),
    ):
        warnings = await app_service._delete_app_from_previous_launchpad(
            app_id=app_id,
            previous_launchpad_instance_ids=[previous_launchpad_id],
        )

    previous_launchpad_admin.delete_app_template_by_app_id.assert_awaited_once_with(
        app_id,
        uninstall=False,
    )
    previous_launchpad_admin.delete_app.assert_awaited_once_with(
        app_id,
        uninstall=False,
    )
    assert warnings == [
        f"This app template was not deleted from previous Launchpad {previous_launchpad_id}; "
        f"please delete this app template manually there (without uninstall)."
    ]


async def test_fetch_source_template_metadata_rejects_ambiguous_source(
    app_service: AppService,
    app_id: UUID,
) -> None:
    result, warnings = await app_service._fetch_source_template_metadata(
        app_id=app_id,
        previous_launchpad_instance_ids=[uuid.uuid4(), uuid.uuid4()],
        template_name="template",
        template_version="v1",
    )

    assert result is None
    assert "more than one source Launchpad" in warnings[0]


async def test_fetch_source_template_metadata_warns_on_identity_mismatch(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    app_id: UUID,
) -> None:
    source_launchpad_id = uuid.uuid4()
    mock_apps_api_client.cluster = "cluster"
    mock_apps_api_client.org_name = "org"
    mock_apps_api_client.project_name = "project"
    source_admin = AsyncMock(spec=LaunchpadAdminApi)
    source_admin.get_app_template.return_value = {
        "name": "source-name",
        "template_name": "other-template",
        "template_version": "v1",
        "verbose_name": "Title",
        "description_short": "",
        "description_long": "",
        "logo": "",
        "documentation_urls": [],
        "external_urls": [],
        "tags": [],
    }

    with patch(
        "launchpad.apps.service.LaunchpadAdminApi.from_outputs",
        new=AsyncMock(return_value=source_admin),
    ):
        result, warnings = await app_service._fetch_source_template_metadata(
            app_id=app_id,
            previous_launchpad_instance_ids=[source_launchpad_id],
            template_name="template",
            template_version="v1",
        )

    assert result is None
    assert "identity does not match" in warnings[0]


@pytest.mark.parametrize(
    ("instance", "warning_fragment"),
    [
        ({"id": "invalid"}, "app id 'invalid' is invalid"),
        (
            {"id": str(uuid.uuid4()), "template_name": "template"},
            "template identity is missing",
        ),
    ],
)
async def test_add_source_branding_validates_candidate(
    app_service: AppService,
    instance: dict[str, object],
    warning_fragment: str,
) -> None:
    result = await app_service._add_source_branding_to_unimported_instance(
        instance,
        asyncio.Semaphore(1),
    )

    assert result["source_branding_launchpad_id"] is None
    assert warning_fragment in result["branding_warnings"][0]
    cast(
        AsyncMock, app_service._app_configurator.prepare_launchpad_auth
    ).assert_not_awaited()


@pytest.mark.parametrize(
    ("installed_app", "templates", "error"),
    [
        (None, [], AppsApiNotFound),
        (
            InstalledApp(
                app_id=uuid.uuid4(),
                app_name="app",
                launchpad_app_name="name",
                is_internal=False,
                is_shared=True,
                user_id=None,
                url="https://app.example.com",
                template_name="name",
                external_url_list=[],
            ),
            [],
            AppsApiNotFound,
        ),
        (
            InstalledApp(
                app_id=uuid.uuid4(),
                app_name="app",
                launchpad_app_name="name",
                is_internal=False,
                is_shared=True,
                user_id=None,
                url="https://app.example.com",
                template_name="name",
                external_url_list=[],
            ),
            [MagicMock(), MagicMock()],
            AppTemplateNameConflict,
        ),
    ],
)
async def test_get_template_by_app_id_errors(
    app_service: AppService,
    installed_app: InstalledApp | None,
    templates: list[MagicMock],
    error: type[Exception],
    app_id: UUID,
) -> None:
    with (
        patch(
            "launchpad.apps.service.select_app",
            new=AsyncMock(return_value=installed_app),
        ),
        patch(
            "launchpad.apps.service.select_templates_by_name",
            new=AsyncMock(return_value=templates),
        ),
        pytest.raises(error),
    ):
        await app_service.get_template_by_app_id(app_id)


@pytest.mark.parametrize(
    "hostname,expected_url",
    [
        ("generated.example", "https://generated.example"),
        ("GENERATED.EXAMPLE.:443", "https://generated.example"),
        ("GENERATED.EXAMPLE.:8443", "https://generated.example:8443"),
    ],
)
async def test_resolve_generated_hostname_uses_local_urls(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    hostname: str,
    expected_url: str,
) -> None:
    installed = MagicMock(spec=InstalledApp)
    mock_apps_api_client.is_static_hostname.return_value = False
    with patch(
        "launchpad.apps.service.select_app_by_any_url",
        new=AsyncMock(return_value=installed),
    ) as by_url:
        assert await app_service.resolve_app_for_authorization(hostname) is installed
    mock_apps_api_client.get_id_by_static_hostname.assert_not_awaited()

    assert by_url.await_args is not None
    assert by_url.await_args.args[1] == expected_url


@pytest.mark.parametrize("current_app_id", [uuid.uuid4(), None])
async def test_resolve_alias_checks_current_binding(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
    current_app_id: UUID | None,
) -> None:
    installed = MagicMock(spec=InstalledApp)
    mock_apps_api_client.get_id_by_static_hostname.return_value = current_app_id
    with (
        patch(
            "launchpad.apps.service.select_app_by_any_url",
            new=AsyncMock(return_value=None),
        ) as by_url,
        patch(
            "launchpad.apps.service.select_app", new=AsyncMock(return_value=installed)
        ) as by_id,
    ):
        result = await app_service.resolve_app_for_authorization(
            "silverfin-dev.apps.apolo.us"
        )
    by_url.assert_awaited_once()
    if current_app_id is None:
        assert result is None
        by_id.assert_not_awaited()
    else:
        assert result is installed
        assert by_id.await_args is not None
        assert by_id.await_args.kwargs["id"] == current_app_id
    mock_apps_api_client.get_id_by_static_hostname.assert_awaited_once_with(
        "silverfin-dev.apps.apolo.us"
    )


async def test_registered_external_hostname_remains_authorized(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
) -> None:
    installed = MagicMock(spec=InstalledApp)
    mock_apps_api_client.is_static_hostname.return_value = False
    with patch(
        "launchpad.apps.service.select_app_by_any_url",
        new=AsyncMock(return_value=installed),
    ):
        assert (
            await app_service.resolve_app_for_authorization(
                "registered.external.example"
            )
            is installed
        )
    mock_apps_api_client.get_id_by_static_hostname.assert_not_awaited()


async def test_stored_static_alias_cannot_override_current_binding(
    app_service: AppService,
    mock_apps_api_client: AsyncMock,
) -> None:
    mock_apps_api_client.is_static_hostname.return_value = True
    mock_apps_api_client.get_id_by_static_hostname.return_value = None
    with patch(
        "launchpad.apps.service.select_app_by_any_url",
        new=AsyncMock(return_value=MagicMock(spec=InstalledApp)),
    ):
        assert (
            await app_service.resolve_app_for_authorization(
                "silverfin-dev.apps.apolo.us"
            )
            is None
        )


async def test_stored_static_hostname_resolves_to_current_app(
    app_service: AppService, mock_apps_api_client: AsyncMock
) -> None:
    previous, current = MagicMock(spec=InstalledApp), MagicMock(spec=InstalledApp)
    previous.app_id, current.app_id = uuid.uuid4(), uuid.uuid4()
    mock_apps_api_client.is_static_hostname.return_value = True
    mock_apps_api_client.get_id_by_static_hostname.return_value = current.app_id
    with (
        patch(
            "launchpad.apps.service.select_app_by_any_url",
            new=AsyncMock(return_value=previous),
        ),
        patch(
            "launchpad.apps.service.select_app", new=AsyncMock(return_value=current)
        ) as by_id,
    ):
        assert (
            await app_service.resolve_app_for_authorization(
                "silverfin-dev.apps.apolo.us"
            )
            is current
        )
    mock_apps_api_client.is_static_hostname.assert_awaited_once_with(
        "silverfin-dev.apps.apolo.us"
    )
    assert by_id.await_args is not None
    assert by_id.await_args.kwargs["id"] == current.app_id
