from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from launchpad.app import Launchpad
from launchpad.apps.registry.base import App, BaseContext
from launchpad.apps.registry.internal.context import InternalAppContext
from launchpad.apps.registry.internal.embeddings import (
    APP_NAME_EMBEDDINGS,
    EmbeddingsApp,
)
from launchpad.apps.registry.internal.llm_inference import (
    APP_NAME_LLM_INFERENCE,
    LlmInferenceApp,
)
from launchpad.apps.registry.internal.postgres import APP_NAME_POSTGRES, PostgresApp
from launchpad.apps.registry.shared.openwebui import (
    APP_NAME_OPEN_WEB_UI,
    OpenWebUIApp,
    OpenWebUIAppContext,
)


@pytest.fixture
def mock_base_context() -> MagicMock:
    return MagicMock(spec=BaseContext)


@pytest.fixture
def mock_internal_app_context() -> MagicMock:
    return MagicMock(spec=InternalAppContext)


@pytest.fixture
def mock_launchpad_app() -> MagicMock:
    return MagicMock(spec=Launchpad)


@pytest.fixture
def mock_request() -> MagicMock:
    request = MagicMock(spec=Request)
    request.app = MagicMock()
    request.app.config = MagicMock()
    request.app.config.apolo = MagicMock()
    request.app.config.apolo.auth_middleware_name = "test-middleware"
    request.app.app_service = MagicMock()
    request.app.app_service.get_installed_app = AsyncMock()
    return request


@pytest.fixture
def mock_openwebui_app_context() -> MagicMock:
    return MagicMock(spec=OpenWebUIAppContext)


class ConcreteApp(App[BaseContext]):
    name = "test-app"
    template_name = "test-template"
    template_version = "1.0"
    is_internal = False
    is_shared = False
    verbose_name = "Test App"
    description_short = "Short description"
    description_long = "Long description"
    logo = "logo.png"
    documentation_urls = []
    external_urls = []
    tags = []

    async def _generate_inputs(self) -> dict[str, str]:
        return {"input_key": "input_value"}


async def test_app_to_apps_api_payload(mock_base_context: MagicMock) -> None:
    app_instance = ConcreteApp(context=mock_base_context)
    payload = await app_instance.to_apps_api_payload()

    assert payload == {
        "template_name": "test-template",
        "template_version": "1.0",
        "input": {"input_key": "input_value"},
    }


# Add a test for merge_with_inputs
def test_internal_app_context_merge_with_inputs() -> None:
    context = InternalAppContext(
        config={"key1": "value1", "nested": {"nkey1": "nvalue1"}}
    )
    inputs = {"key1": "new_value1", "key2": "value2", "nested": {"nkey2": "nvalue2"}}

    merged = context.merge_with_inputs(inputs)
    assert merged == {
        "key1": "value1",  # Context overwrites inputs
        "key2": "value2",
        "nested": {"nkey1": "nvalue1", "nkey2": "nvalue2"},  # Nested dicts are merged
    }

    # Test with lists
    context_list = InternalAppContext(config={"list_key": [1, 2]})
    inputs_list = {"list_key": [3, 4]}
    merged_list = context_list.merge_with_inputs(inputs_list)
    assert merged_list == {
        "list_key": [3, 4, 1, 2]
    }  # Inputs list is extended by context list

    # Test with different types
    context_diff_type = InternalAppContext(config={"diff_key": "string"})
    inputs_diff_type = {"diff_key": 123}
    merged_diff_type = context_diff_type.merge_with_inputs(inputs_diff_type)
    assert merged_diff_type == {"diff_key": "string"}  # Context overwrites inputs


def test_embeddings_app_attributes(mock_internal_app_context: MagicMock) -> None:
    app = EmbeddingsApp(context=mock_internal_app_context)

    assert app.name == APP_NAME_EMBEDDINGS
    assert app.template_name == "text-embeddings-inference"
    assert app.template_version == "v25.7.0"
    assert app.is_internal is True
    assert app.is_shared is True
    assert app.verbose_name == "Embeddings"
    assert app.description_short == "Embeddings"
    assert app.description_long == "Embeddings"
    assert app.logo == ""
    assert app.documentation_urls == []
    assert app.external_urls == []
    assert app.tags == []


async def test_embeddings_app_generate_inputs(
    mock_internal_app_context: MagicMock,
) -> None:
    mock_internal_app_context.config = {"embeddings_config": "value"}
    mock_internal_app_context.merge_with_inputs.return_value = {
        "merged_config": "value"
    }

    app = EmbeddingsApp(context=mock_internal_app_context)
    inputs = await app._generate_inputs()

    assert inputs == {"merged_config": "value"}
    mock_internal_app_context.merge_with_inputs.assert_called_once_with(
        inputs={
            "ingress_http": None,
            "displayName": APP_NAME_EMBEDDINGS,
            "extra_env_vars": [],
        }
    )


def test_llm_inference_app_attributes(mock_internal_app_context: MagicMock) -> None:
    app = LlmInferenceApp(context=mock_internal_app_context)

    assert app.name == APP_NAME_LLM_INFERENCE
    assert app.template_name == "llm-inference"
    assert app.template_version == "v25.10.0"
    assert app.is_internal is True
    assert app.is_shared is True
    assert app.verbose_name == "LLM Inference"
    assert app.description_short == "LLM Inference"
    assert app.description_long == "LLM Inference"
    assert app.logo == ""
    assert app.documentation_urls == []
    assert app.external_urls == []
    assert app.tags == []


async def test_llm_inference_app_generate_inputs(
    mock_internal_app_context: MagicMock,
) -> None:
    mock_internal_app_context.config = {"llm_config": "value"}
    mock_internal_app_context.merge_with_inputs.return_value = {
        "merged_config": "value"
    }

    app = LlmInferenceApp(context=mock_internal_app_context)
    inputs = await app._generate_inputs()

    assert inputs == {"merged_config": "value"}
    mock_internal_app_context.merge_with_inputs.assert_called_once_with(
        inputs={
            "ingress_http": None,
            "tokenizer_hf_name": "meta-llama/Llama-3.1-8B-Instruct",
            "cache_config": None,
            "displayName": APP_NAME_LLM_INFERENCE,
            "extra_env_vars": [],
        }
    )


def test_postgres_app_attributes(mock_internal_app_context: MagicMock) -> None:
    app = PostgresApp(context=mock_internal_app_context)

    assert app.name == APP_NAME_POSTGRES
    assert app.template_name == "postgres"
    assert app.template_version == "latest"
    assert app.is_internal is True
    assert app.is_shared is True
    assert app.verbose_name == "PostgreSQL"
    assert app.description_short == "PostgreSQL"
    assert app.description_long == "PostgreSQL"
    assert app.logo == ""
    assert app.documentation_urls == []
    assert app.external_urls == []
    assert app.tags == []


async def test_postgres_app_generate_inputs(
    mock_internal_app_context: MagicMock,
) -> None:
    mock_internal_app_context.config = {"postgres_config": "value"}
    mock_internal_app_context.merge_with_inputs.return_value = {
        "merged_config": "value"
    }

    app = PostgresApp(context=mock_internal_app_context)
    inputs = await app._generate_inputs()

    assert inputs == {"merged_config": "value"}
    mock_internal_app_context.merge_with_inputs.assert_called_once_with(
        inputs={
            "postgres_config": {
                "postgres_version": "16",
                "instance_replicas": 1,
                "instance_size": 1,
                "db_users": [{"name": "user", "db_names": ["openwebui"]}],
            },
            "pg_bouncer": {"replicas": 1},
            "displayName": APP_NAME_POSTGRES,
        }
    )


def test_openwebui_app_attributes(mock_openwebui_app_context: MagicMock) -> None:
    app = OpenWebUIApp(context=mock_openwebui_app_context)

    assert app.name == APP_NAME_OPEN_WEB_UI
    assert app.template_name == "openwebui"
    assert app.template_version == "latest"
    assert app.is_internal is False
    assert app.is_shared is True
    assert app.verbose_name == "OpenWebUI"


async def test_openwebui_app_context_from_request(mock_request: MagicMock) -> None:
    # Mock get_installed_app to return a dummy InstalledApp
    mock_request.app.app_service.get_installed_app.return_value = MagicMock(
        app_id="mock-app-id"
    )

    context = await OpenWebUIAppContext.from_request(mock_request)
    assert isinstance(context, OpenWebUIAppContext)
    assert context.auth_middleware_name == "test-middleware"
    # Assert that get_installed_app was called for required apps
    mock_request.app.app_service.get_installed_app.assert_any_call(
        APP_NAME_LLM_INFERENCE, with_url=False
    )
    mock_request.app.app_service.get_installed_app.assert_any_call(
        APP_NAME_EMBEDDINGS, with_url=False
    )
    mock_request.app.app_service.get_installed_app.assert_any_call(
        APP_NAME_POSTGRES, with_url=False
    )
