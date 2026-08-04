import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponseError

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


async def test_launchpad_admin_api_gets_template_by_instance_directly() -> None:
    http = AsyncMock()
    app_id = uuid.uuid4()
    login_response = MagicMock()
    login_response.text = AsyncMock(return_value='{"access_token": "token"}')
    login_response.raise_for_status.return_value = None
    login_response.json = AsyncMock(return_value={"access_token": "token"})
    get_response = MagicMock()
    get_response.status = 200
    get_response.text = AsyncMock(return_value="{}")
    get_response.raise_for_status.return_value = None
    get_response.json = AsyncMock(return_value={"name": "branded-app"})
    http.post.return_value = login_response
    http.get.return_value = get_response

    admin_api = LaunchpadAdminApi(
        http=http,
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )

    assert await admin_api.get_app_template(app_id) == {"name": "branded-app"}
    http.get.assert_awaited_once_with(
        f"https://launchpad-api.example.com/api/v1/apps/templates/by-instance/{app_id}",
        headers={"Authorization": "Bearer token"},
        ssl=False,
    )


async def test_launchpad_admin_api_falls_back_to_legacy_list_endpoints() -> None:
    http = AsyncMock()
    app_id = uuid.uuid4()
    login_response = MagicMock()
    login_response.text = AsyncMock(return_value='{"access_token": "token"}')
    login_response.raise_for_status.return_value = None
    login_response.json = AsyncMock(return_value={"access_token": "token"})

    not_found = MagicMock(status=404)
    instances = MagicMock(status=200)
    instances.text = AsyncMock(return_value="{}")
    instances.raise_for_status.return_value = None
    instances.json = AsyncMock(
        return_value={
            "items": [{"app_id": str(app_id), "template_name": "branded-app"}],
            "pages": 1,
        }
    )
    templates = MagicMock(status=200)
    templates.text = AsyncMock(return_value="{}")
    templates.raise_for_status.return_value = None
    templates.json = AsyncMock(
        return_value={
            "items": [{"name": "branded-app", "verbose_name": "Branded"}],
            "pages": 1,
        }
    )
    http.post.return_value = login_response
    http.get.side_effect = [not_found, instances, templates]

    admin_api = LaunchpadAdminApi(
        http=http,
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )

    result = await admin_api.get_app_template(app_id)

    assert result["verbose_name"] == "Branded"
    assert http.get.await_count == 3


async def test_launchpad_admin_api_get_rejects_http_error() -> None:
    http = AsyncMock()
    response = MagicMock(status=500)
    response.text = AsyncMock(return_value="failure")
    response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(), history=(), status=500
    )
    http.get.return_value = response
    admin_api = LaunchpadAdminApi(
        http=http,
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )
    admin_api._access_token = "token"

    with pytest.raises(LaunchpadApiError, match="admin GET request failed"):
        await admin_api._authorized_get_json("/test")


async def test_launchpad_admin_api_get_rejects_non_object_response() -> None:
    http = AsyncMock()
    response = MagicMock(status=200)
    response.text = AsyncMock(return_value="[]")
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value=[])
    http.get.return_value = response
    admin_api = LaunchpadAdminApi(
        http=http,
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )
    admin_api._access_token = "token"

    with pytest.raises(LaunchpadApiError, match="response is malformed"):
        await admin_api._authorized_get_json("/test")


@pytest.mark.parametrize(
    "payload",
    [None, {"items": "invalid", "pages": 1}],
)
async def test_launchpad_admin_api_list_rejects_malformed_pages(
    payload: dict[str, object] | None,
) -> None:
    admin_api = LaunchpadAdminApi(
        http=AsyncMock(),
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )
    admin_api._authorized_get_json = AsyncMock(return_value=payload)  # type: ignore[method-assign]

    with pytest.raises(LaunchpadApiError):
        await admin_api._list_all("/test")


async def test_launchpad_admin_api_list_reads_all_pages() -> None:
    admin_api = LaunchpadAdminApi(
        http=AsyncMock(),
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )
    admin_api._authorized_get_json = AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            {"items": [{"id": 1}], "pages": 2},
            {"items": [{"id": 2}], "pages": 2},
        ]
    )

    assert await admin_api._list_all("/test") == [{"id": 1}, {"id": 2}]


@pytest.mark.parametrize(
    ("instances", "templates", "message"),
    [
        ([], [], "Expected one source app"),
        ([{"app_id": "APP_ID"}], [], "does not identify its template"),
        (
            [{"app_id": "APP_ID", "template_name": "name"}],
            [],
            "Expected one source template",
        ),
    ],
)
async def test_launchpad_admin_api_legacy_lookup_validation(
    instances: list[dict[str, object]],
    templates: list[dict[str, object]],
    message: str,
) -> None:
    app_id = uuid.uuid4()
    normalized_instances = [
        {**instance, "app_id": str(app_id)}
        if instance.get("app_id") == "APP_ID"
        else instance
        for instance in instances
    ]
    admin_api = LaunchpadAdminApi(
        http=AsyncMock(),
        base_url="https://launchpad-api.example.com",
        username="admin",
        password="password",
    )
    admin_api._authorized_get_json = AsyncMock(return_value=None)  # type: ignore[method-assign]
    admin_api._list_all = AsyncMock(  # type: ignore[method-assign]
        side_effect=[normalized_instances, templates]
    )

    with pytest.raises(LaunchpadApiError, match=message):
        await admin_api.get_app_template(app_id)


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
