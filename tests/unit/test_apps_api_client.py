import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from aiohttp import ClientResponseError

from launchpad.ext.apps_api import AppsApiClient, AppsApiError, NotFound, ServerError


@pytest.fixture
def mock_http_session() -> AsyncMock:
    return AsyncMock()


@pytest.mark.parametrize(
    "hostname", ["silverfin-dev.apps.apolo.us", "SILVERFIN-DEV.APPS.APOLO.US.:443"]
)
async def test_get_id_by_static_hostname(
    apps_api_client: AppsApiClient, app_id: UUID, hostname: str
) -> None:
    with patch.object(
        apps_api_client,
        "_request",
        new=AsyncMock(
            side_effect=[
                {"items": [{"id": str(app_id)}]},
                {
                    "hostname": "silverfin-dev.apps.apolo.us",
                    "phase": "active",
                    "static_url": "https://silverfin-dev.apps.apolo.us",
                },
            ]
        ),
    ) as request:
        assert await apps_api_client.get_id_by_static_hostname(hostname) == app_id
    request.assert_any_await(
        method="GET",
        url="https://api.example.com/v2/instances",
        params={"hostname": "silverfin-dev.apps.apolo.us"},
    )

    request.assert_any_await(
        method="GET",
        url=f"https://api.example.com/v2/instances/{app_id}/static-hostname",
    )


@pytest.mark.parametrize("missing_binding", [False, True])
async def test_get_id_by_static_hostname_inactive(
    apps_api_client: AppsApiClient, app_id: UUID, missing_binding: bool
) -> None:
    responses: list[Any] = [NotFound()]
    if missing_binding:
        responses.insert(0, {"items": [{"id": str(app_id)}]})
    with patch.object(
        apps_api_client, "_request", new=AsyncMock(side_effect=responses)
    ):
        assert (
            await apps_api_client.get_id_by_static_hostname("detached.apps.apolo.us")
            is None
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"items": []},
        {"items": [{"id": "bad"}]},
        {"items": [{"id": str(uuid.uuid4())}, {"id": str(uuid.uuid4())}]},
    ],
)
async def test_get_id_by_static_hostname_invalid_response(
    apps_api_client: AppsApiClient, payload: dict[str, Any]
) -> None:
    with (
        patch.object(apps_api_client, "_request", new=AsyncMock(return_value=payload)),
        pytest.raises(AppsApiError),
    ):
        await apps_api_client.get_id_by_static_hostname("silverfin-dev.apps.apolo.us")


@pytest.fixture
def apps_api_client(mock_http_session: AsyncMock) -> AppsApiClient:
    return AppsApiClient(
        http=mock_http_session,
        base_url="https://api.example.com",
        token="test-token",
        cluster="test-cluster",
        org_name="test-org",
        project_name="test-project",
    )


@pytest.fixture
def app_id() -> UUID:
    return uuid.uuid4()


def test_extract_service_api_urls_with_service_apis(
    apps_api_client: AppsApiClient,
) -> None:
    """Test extraction of URLs from ServiceAPI objects"""
    outputs = {
        "chat_api": {
            "__type__": "ServiceAPI[OpenAICompatChatAPI]",
            "external_url": {
                "protocol": "https",
                "host": "llm-inference.apps.dev.apolo.us",
                "base_path": "/",
            },
        },
        "embeddings_api": {
            "__type__": "ServiceAPI[OpenAICompatEmbeddingsAPI]",
            "external_url": {
                "protocol": "https",
                "host": "llm-inference.apps.dev.apolo.us",
                "base_path": "/v1",
            },
        },
        "some_other_field": "value",
    }

    urls = apps_api_client._extract_service_api_urls(outputs)

    assert len(urls) == 2
    assert "https://llm-inference.apps.dev.apolo.us" in urls
    assert "https://llm-inference.apps.dev.apolo.us/v1" in urls


def test_extract_service_api_urls_nested(apps_api_client: AppsApiClient) -> None:
    """Test extraction of URLs from nested ServiceAPI objects"""
    outputs = {
        "nested": {
            "chat_api": {
                "__type__": "ServiceAPI[OpenAICompatChatAPI]",
                "external_url": {
                    "protocol": "https",
                    "host": "example.com",
                    "base_path": "/api",
                },
            }
        }
    }

    urls = apps_api_client._extract_service_api_urls(outputs)

    assert len(urls) == 1
    assert "https://example.com/api" in urls


def test_extract_service_api_urls_empty(apps_api_client: AppsApiClient) -> None:
    """Test extraction returns empty list when no ServiceAPI objects found"""
    outputs: dict[str, Any] = {"some_field": "value", "another_field": 123}

    urls = apps_api_client._extract_service_api_urls(outputs)

    assert urls == []


def test_extract_service_api_urls_missing_fields(
    apps_api_client: AppsApiClient,
) -> None:
    """Test extraction handles missing protocol/host gracefully"""
    outputs = {
        "incomplete_api": {
            "__type__": "ServiceAPI[SomeAPI]",
            "external_url": {
                "base_path": "/api",
                # Missing protocol and host
            },
        }
    }

    urls = apps_api_client._extract_service_api_urls(outputs)

    assert urls == []


async def test_get_app_endpoints_with_app_url_and_service_apis(
    apps_api_client: AppsApiClient, app_id: UUID
) -> None:
    """Test get_app_endpoints extracts both main URL and ServiceAPI URLs"""
    mock_outputs = {
        "app_url": {
            "external_url": {
                "protocol": "https",
                "host": "myapp.example.com",
            }
        },
        "chat_api": {
            "__type__": "ServiceAPI[OpenAICompatChatAPI]",
            "external_url": {
                "protocol": "https",
                "host": "api.example.com",
                "base_path": "/v1",
            },
        },
    }

    # Mock the get_outputs method
    with patch.object(
        apps_api_client, "get_outputs", new=AsyncMock(return_value=mock_outputs)
    ):
        main_url, external_urls = await apps_api_client.get_app_endpoints(app_id)

        assert main_url == "https://myapp.example.com"
        assert len(external_urls) == 1
        assert "https://api.example.com/v1" in external_urls


async def test_get_app_endpoints_no_app_url(
    apps_api_client: AppsApiClient, app_id: UUID
) -> None:
    """Test get_app_endpoints when app_url is null"""
    mock_outputs = {
        "app_url": None,
        "chat_api": {
            "__type__": "ServiceAPI[OpenAICompatChatAPI]",
            "external_url": {
                "protocol": "https",
                "host": "api.example.com",
                "base_path": "/",
            },
        },
    }

    with patch.object(
        apps_api_client, "get_outputs", new=AsyncMock(return_value=mock_outputs)
    ):
        main_url, external_urls = await apps_api_client.get_app_endpoints(app_id)

        assert main_url is None
        assert len(external_urls) == 1
        assert "https://api.example.com" in external_urls


async def test_get_app_endpoints_empty_outputs(
    apps_api_client: AppsApiClient, app_id: UUID
) -> None:
    """Test get_app_endpoints with empty outputs"""
    mock_outputs: dict[str, Any] = {}

    with patch.object(
        apps_api_client, "get_outputs", new=AsyncMock(return_value=mock_outputs)
    ):
        main_url, external_urls = await apps_api_client.get_app_endpoints(app_id)

        assert main_url is None
        assert external_urls == []


async def test_get_by_id_not_found(
    apps_api_client: AppsApiClient, app_id: UUID, mock_http_session: AsyncMock
) -> None:
    """Test get_by_id raises NotFound on 404 response"""
    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status = 404
    mock_text = AsyncMock(return_value="Not found")
    mock_response.text = mock_text
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="Not Found",
    )
    mock_http_session.request.return_value = mock_response

    with pytest.raises(NotFound):
        await apps_api_client.get_by_id(app_id)


async def test_get_template_not_found(
    apps_api_client: AppsApiClient, mock_http_session: AsyncMock
) -> None:
    """Test get_template raises NotFound on 404 response"""
    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status = 404
    mock_text = AsyncMock(return_value="Template not found")
    mock_response.text = mock_text
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="Not Found",
    )
    mock_http_session.request.return_value = mock_response

    with pytest.raises(NotFound):
        await apps_api_client.get_template("nonexistent-template", "1.0.0")


async def test_get_outputs_not_found(
    apps_api_client: AppsApiClient, app_id: UUID, mock_http_session: AsyncMock
) -> None:
    """Test get_outputs raises NotFound on 404 response"""
    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status = 404
    mock_text = AsyncMock(return_value="App not found")
    mock_response.text = mock_text
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="Not Found",
    )
    mock_http_session.request.return_value = mock_response

    with pytest.raises(NotFound):
        await apps_api_client.get_outputs(app_id)


async def test_get_inputs_not_found(
    apps_api_client: AppsApiClient, app_id: UUID, mock_http_session: AsyncMock
) -> None:
    """Test get_inputs raises NotFound on 404 response"""
    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status = 404
    mock_text = AsyncMock(return_value="App not found")
    mock_response.text = mock_text
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="Not Found",
    )
    mock_http_session.request.return_value = mock_response

    with pytest.raises(NotFound):
        await apps_api_client.get_inputs(app_id)


async def test_delete_app_not_found(
    apps_api_client: AppsApiClient, app_id: UUID, mock_http_session: AsyncMock
) -> None:
    """Test delete_app raises NotFound on 404 response"""
    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status = 404
    mock_text = AsyncMock(return_value="App not found")
    mock_response.text = mock_text
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="Not Found",
    )
    mock_http_session.request.return_value = mock_response

    with pytest.raises(NotFound):
        await apps_api_client.delete_app(app_id)


async def test_configure_app_sends_reconfigure_payload(
    apps_api_client: AppsApiClient, app_id: UUID, mock_http_session: AsyncMock
) -> None:
    mock_response = MagicMock()
    mock_response.text = AsyncMock(return_value='{"id": "app"}')
    mock_response.raise_for_status.return_value = None
    mock_response.json = AsyncMock(return_value={"id": str(app_id)})
    mock_http_session.request.return_value = mock_response

    inputs = {"networking": {"ingress_http": {"auth": {"type": "custom_auth"}}}}

    result = await apps_api_client.configure_app(
        app_id=app_id,
        inputs=inputs,
        comment="Import into Launchpad abc: change auth middleware",
    )

    assert result == {"id": str(app_id)}
    mock_http_session.request.assert_awaited_once_with(
        "PUT",
        f"https://api.example.com/v1/cluster/test-cluster/org/test-org/project/test-project/instances/{app_id}",
        headers={"Authorization": "Bearer test-token"},
        ssl=False,
        json={
            "input": inputs,
            "comment": "Import into Launchpad abc: change auth middleware",
        },
    )


async def test_get_app_endpoints_not_found(
    apps_api_client: AppsApiClient, app_id: UUID, mock_http_session: AsyncMock
) -> None:
    """Test get_app_endpoints raises NotFound when app doesn't exist"""
    # Mock 404 response for get_outputs (called by get_app_endpoints)
    mock_response = MagicMock()
    mock_response.status = 404
    mock_text = AsyncMock(return_value="App not found")
    mock_response.text = mock_text
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="Not Found",
    )
    mock_http_session.request.return_value = mock_response

    with pytest.raises(NotFound):
        await apps_api_client.get_app_endpoints(app_id)


async def test_server_error_500(
    apps_api_client: AppsApiClient, app_id: UUID, mock_http_session: AsyncMock
) -> None:
    """Test that 500 responses raise ServerError"""
    # Mock 500 response
    mock_response = MagicMock()
    mock_response.status = 500
    mock_text = AsyncMock(return_value="Internal server error")
    mock_response.text = mock_text
    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=500,
        message="Internal Server Error",
    )
    mock_http_session.request.return_value = mock_response

    with pytest.raises(ServerError):
        await apps_api_client.get_by_id(app_id)


@pytest.mark.parametrize(
    "binding",
    [
        {
            "hostname": "silverfin-dev.apps.apolo.us",
            "phase": "reserved",
            "static_url": None,
        },
        {
            "hostname": "silverfin-dev.apps.apolo.us",
            "phase": "active",
            "static_url": None,
        },
        {
            "hostname": "other.apps.apolo.us",
            "phase": "active",
            "static_url": "https://other.apps.apolo.us",
        },
    ],
)
async def test_static_hostname_requires_exact_active_binding(
    apps_api_client: AppsApiClient, app_id: UUID, binding: dict[str, Any]
) -> None:
    with patch.object(
        apps_api_client,
        "_request",
        new=AsyncMock(side_effect=[{"items": [{"id": str(app_id)}]}, binding]),
    ):
        assert (
            await apps_api_client.get_id_by_static_hostname(
                "silverfin-dev.apps.apolo.us"
            )
            is None
        )


async def test_static_hostname_rejects_name_lookup_on_attacker_domain(
    apps_api_client: AppsApiClient, app_id: UUID
) -> None:
    binding = {
        "hostname": "silverfin-dev.apps.apolo.us",
        "phase": "active",
        "static_url": "https://silverfin-dev.apps.apolo.us",
    }
    with patch.object(
        apps_api_client,
        "_request",
        new=AsyncMock(side_effect=[{"items": [{"id": str(app_id)}]}, binding]),
    ):
        assert (
            await apps_api_client.get_id_by_static_hostname(
                "silverfin-dev.attacker.example"
            )
            is None
        )


@pytest.mark.parametrize(
    "hostname,expected",
    [
        ("silverfin-dev.apps.apolo.us", True),
        ("silverfin-dev.apps.apolo.us:443", True),
        ("SILVERFIN-DEV.apps.apolo.us.", True),
        ("silverfin-dev.attacker.example", False),
        ("evilapps.apolo.us", False),
    ],
)
async def test_static_hostname_namespace(
    apps_api_client: AppsApiClient, hostname: str, expected: bool
) -> None:
    with patch.object(
        apps_api_client,
        "_request",
        new=AsyncMock(return_value={"hostname_domain": "apps.apolo.us"}),
    ):
        assert await apps_api_client.is_static_hostname(hostname) is expected


@pytest.mark.parametrize("binding_response", [{}, ServerError()])
async def test_static_hostname_binding_failure_is_not_a_missing_binding(
    apps_api_client: AppsApiClient,
    app_id: UUID,
    binding_response: dict[str, Any] | ServerError,
) -> None:
    with (
        patch.object(
            apps_api_client,
            "_request",
            new=AsyncMock(
                side_effect=[{"items": [{"id": str(app_id)}]}, binding_response]
            ),
        ),
        pytest.raises(AppsApiError),
    ):
        await apps_api_client.get_id_by_static_hostname("silverfin-dev.apps.apolo.us")


async def test_unconfigured_static_hostname_namespace_is_false(
    apps_api_client: AppsApiClient,
) -> None:
    with patch.object(
        apps_api_client, "_request", new=AsyncMock(side_effect=NotFound())
    ):
        assert not await apps_api_client.is_static_hostname(
            "registered.external.example"
        )


@pytest.mark.parametrize("response", [ServerError(), {}, {"hostname_domain": ""}])
async def test_static_hostname_configuration_failure_is_not_disabled(
    apps_api_client: AppsApiClient, response: ServerError | dict[str, Any]
) -> None:
    with (
        patch.object(
            apps_api_client, "_request", new=AsyncMock(side_effect=[response])
        ),
        pytest.raises(AppsApiError),
    ):
        await apps_api_client.is_static_hostname("registered.external.example")
