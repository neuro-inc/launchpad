import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from launchpad.ext.apps_api import AppsApiClient


@pytest.fixture
def mock_http_session() -> AsyncMock:
    return AsyncMock()


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
