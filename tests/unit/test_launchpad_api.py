import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from launchpad.ext.launchpad_api import (
    LaunchpadAdminApi,
    LaunchpadApiError,
    _service_api_to_url,
)


def test_service_api_to_url_prefers_external_url() -> None:
    assert (
        _service_api_to_url(
            {
                "internal_url": {
                    "protocol": "http",
                    "host": "internal",
                    "base_path": "/",
                },
                "external_url": {
                    "protocol": "https",
                    "host": "launchpad-api.example.com",
                    "base_path": "/",
                },
            }
        )
        == "https://launchpad-api.example.com"
    )


async def test_launchpad_admin_api_builds_from_outputs() -> None:
    http = AsyncMock()
    apolo_client = MagicMock()
    apolo_client.secrets.get = AsyncMock(return_value=b"password")

    admin_api = await LaunchpadAdminApi.from_outputs(
        http=http,
        apolo_client=apolo_client,
        cluster_name="test-cluster",
        org_name="test-org",
        project_name="test-project",
        outputs={
            "admin_api": {
                "api_url": {
                    "external_url": {
                        "protocol": "https",
                        "host": "launchpad-api.example.com",
                        "base_path": "/",
                    }
                }
            },
            "admin_user": {
                "username": "admin",
                "password": {"key": "launchpad-admin-secret"},
            },
        },
    )

    assert isinstance(admin_api, LaunchpadAdminApi)
    apolo_client.secrets.get.assert_awaited_once_with(
        "launchpad-admin-secret",
        cluster_name="test-cluster",
        org_name="test-org",
        project_name="test-project",
    )


async def test_launchpad_admin_api_delete_app_template_by_app_id() -> None:
    http = AsyncMock()
    app_id = uuid.uuid4()
    login_response = MagicMock()
    login_response.text = AsyncMock(return_value='{"access_token": "token"}')
    login_response.raise_for_status.return_value = None
    login_response.json = AsyncMock(return_value={"access_token": "token"})
    delete_response = MagicMock()
    delete_response.status = 204
    delete_response.text = AsyncMock(return_value="")
    delete_response.raise_for_status.return_value = None
    http.post.return_value = login_response
    http.delete.return_value = delete_response

    admin_api = LaunchpadAdminApi(
        http=http,
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )
    deleted = await admin_api.delete_app_template_by_app_id(app_id, uninstall=False)

    assert deleted is True
    http.post.assert_awaited_once_with(
        "https://launchpad-api.example.com/auth/token",
        json={"username": "admin", "password": "password"},
        ssl=False,
    )
    http.delete.assert_awaited_once_with(
        f"https://launchpad-api.example.com/api/v1/apps/templates/by-instance/{app_id}",
        params={"uninstall": "false"},
        headers={"Authorization": "Bearer token"},
        ssl=False,
    )


async def test_launchpad_admin_api_reuses_access_token() -> None:
    http = AsyncMock()
    login_response = MagicMock()
    login_response.text = AsyncMock(return_value='{"access_token": "token"}')
    login_response.raise_for_status.return_value = None
    login_response.json = AsyncMock(return_value={"access_token": "token"})
    delete_response = MagicMock()
    delete_response.status = 204
    delete_response.text = AsyncMock(return_value="")
    delete_response.raise_for_status.return_value = None
    http.post.return_value = login_response
    http.delete.return_value = delete_response

    admin_api = LaunchpadAdminApi(
        http=http,
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )

    await admin_api.delete_app_template_by_app_id(uuid.uuid4(), uninstall=False)
    await admin_api.delete_app(uuid.uuid4(), uninstall=False)

    http.post.assert_awaited_once()


async def test_launchpad_admin_api_delete_app_template_by_app_id_returns_false_on_404() -> (
    None
):
    http = AsyncMock()
    app_id = uuid.uuid4()
    login_response = MagicMock()
    login_response.text = AsyncMock(return_value='{"access_token": "token"}')
    login_response.raise_for_status.return_value = None
    login_response.json = AsyncMock(return_value={"access_token": "token"})
    delete_response = MagicMock()
    delete_response.status = 404
    delete_response.text = AsyncMock(return_value="")
    http.post.return_value = login_response
    http.delete.return_value = delete_response

    admin_api = LaunchpadAdminApi(
        http=http,
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )

    deleted = await admin_api.delete_app_template_by_app_id(app_id, uninstall=False)

    assert deleted is False


async def test_launchpad_admin_api_warns_when_secret_cannot_be_resolved() -> None:
    apolo_client = MagicMock()
    apolo_client.secrets.get = AsyncMock(side_effect=RuntimeError("no access"))

    with pytest.raises(
        LaunchpadApiError, match="admin password secret could not be resolved"
    ):
        await LaunchpadAdminApi.from_outputs(
            http=AsyncMock(),
            apolo_client=apolo_client,
            cluster_name="test-cluster",
            org_name="test-org",
            project_name="test-project",
            outputs={
                "admin_api": {
                    "api_url": {
                        "external_url": {
                            "protocol": "https",
                            "host": "launchpad-api.example.com",
                            "base_path": "/",
                        }
                    }
                },
                "admin_user": {
                    "username": "admin",
                    "password": {"key": "launchpad-admin-secret"},
                },
            },
        )


@pytest.mark.parametrize(
    "service_api",
    [
        {},
        {"external_url": {"protocol": "https"}},
        {"external_url": {"host": "launchpad-api.example.com"}},
    ],
)
def test_service_api_to_url_returns_none_for_incomplete_values(
    service_api: dict[str, object],
) -> None:
    assert _service_api_to_url(service_api) is None
