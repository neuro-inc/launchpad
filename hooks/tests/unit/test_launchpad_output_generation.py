from unittest.mock import AsyncMock, call, patch

import pytest
from apolo_app_types import ApoloSecret
from apolo_apps_launchpad.outputs_processor import get_launchpad_outputs
from apolo_sdk import Client


KEYCLOAK_HELM_VALUES = {
    "keycloak": {
        "auth": {
            "adminPassword": "test-admin-password",
        }
    },
    "apolo_app_id": "test-app-id",
    "APOLO_PASSED_CONFIG": "someconfig",
    "LAUNCHPAD_ADMIN_USER": "admin",
    "LAUNCHPAD_ADMIN_EMAIL": "admin@example.com",
    "LAUNCHPAD_ADMIN_PASSWORD": "admin-password",
    "dbPassword": "test-db-password",
}


async def create_apolo_secret(*args, **kwargs):
    return ApoloSecret(key="secret=key")


async def test_frontend_output_references_the_previously_persisted_secret(
    setup_clients: Client,
    mock_kubernetes_client: object,
    app_instance_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    creator = AsyncMock(return_value=ApoloSecret(key="secret-key"))
    monkeypatch.setattr(
        "apolo_app_types.outputs.utils.apolo_secrets.create_apolo_secret", creator
    )
    result = await get_launchpad_outputs(
        helm_values={
            **KEYCLOAK_HELM_VALUES,
            "frontend": {"image": {"digest": "sha256:" + "a" * 64}},
        },
        app_instance_id=app_instance_id,
    )
    assert (
        result["frontend_session_secret"]["key"]
        == "launchpad-frontend-session-test-app-id"
    )
    assert sorted(request.kwargs["key"] for request in creator.await_args_list) == [
        "keycloak-admin-pswd",
        "keycloak-db-pswd",
        "launchpad-admin-pswd",
    ]


async def test_output_secret_failure_uses_the_shared_retry_policy(
    setup_clients: Client,
    mock_kubernetes_client: object,
    app_instance_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    creator = AsyncMock(side_effect=RuntimeError("Secret storage is unavailable."))
    sleeper = AsyncMock()
    monkeypatch.setattr(
        "apolo_app_types.outputs.utils.apolo_secrets.create_apolo_secret", creator
    )
    with patch("apolo_app_types.outputs.utils.apolo_secrets.asyncio.sleep", sleeper):
        with pytest.raises(RuntimeError, match="Secret storage is unavailable"):
            await get_launchpad_outputs(KEYCLOAK_HELM_VALUES, app_instance_id)
    assert creator.await_count == 5
    assert sleeper.await_args_list == [call(delay) for delay in (2, 4, 8, 16)]


@pytest.mark.asyncio
async def test_launchpad_output_generation(
    setup_clients, mock_kubernetes_client, app_instance_id, monkeypatch
):
    monkeypatch.setattr(
        "apolo_app_types.outputs.utils.apolo_secrets.create_apolo_secret",
        create_apolo_secret,
    )
    """Test launchpad output generation for app_url."""
    res = await get_launchpad_outputs(
        helm_values={
            "LAUNCHPAD_INITIAL_CONFIG": {
                "vllm": {
                    "hugging_face_model": {
                        "model_hf_name": "meta-llama/Llama-3.1-8B-Instruct"
                    },
                    "preset": {"name": "gpu-small"},
                }
            },
            **KEYCLOAK_HELM_VALUES,
        },
        app_instance_id=app_instance_id,
    )

    assert res
    assert "app_url" in res

    app_url = res["app_url"]
    assert app_url["internal_url"] == {
        "__type__": "WebApp",
        "api_type": "webapp",
        "base_path": "/",
        "host": "app.default-namespace",
        "port": 80,
        "protocol": "http",
        "timeout": 30.0,
    }
    assert app_url["external_url"] == {
        "__type__": "WebApp",
        "api_type": "webapp",
        "base_path": "/",
        "host": "example.com",
        "port": 80,
        "protocol": "https",
        "timeout": 30.0,
    }


@pytest.mark.asyncio
async def test_launchpad_output_generation_no_external_url(
    setup_clients, mock_kubernetes_client, app_instance_id, monkeypatch
):
    """Test launchpad output generation when no external URL is available."""

    async def mock_get_service_host_port(*args, **kwargs):
        return ("app.default-namespace", 80)

    async def mock_get_ingress_host_port(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "apolo_app_types.outputs.utils.apolo_secrets.create_apolo_secret",
        create_apolo_secret,
    )
    monkeypatch.setattr(
        "apolo_apps_launchpad.outputs_processor.get_service_host_port",
        mock_get_service_host_port,
    )
    monkeypatch.setattr(
        "apolo_apps_launchpad.outputs_processor.get_ingress_host_port",
        mock_get_ingress_host_port,
    )

    res = await get_launchpad_outputs(
        helm_values={
            "LAUNCHPAD_INITIAL_CONFIG": {
                "vllm": {
                    "hugging_face_model": {
                        "model_hf_name": "unsloth/Magistral-Small-2506-GGUF"
                    },
                    "preset": {"name": "gpu-medium"},
                }
            },
            **KEYCLOAK_HELM_VALUES,
        },
        app_instance_id=app_instance_id,
    )

    assert res
    assert "app_url" in res

    app_url = res["app_url"]
    assert app_url["internal_url"] == {
        "__type__": "WebApp",
        "api_type": "webapp",
        "base_path": "/",
        "host": "app.default-namespace",
        "port": 80,
        "protocol": "http",
        "timeout": 30.0,
    }
    assert app_url["external_url"] is None


@pytest.mark.asyncio
async def test_launchpad_output_generation_no_service(
    setup_clients, mock_kubernetes_client, app_instance_id, monkeypatch
):
    """Test launchpad output generation when no service is available."""

    async def mock_get_service_host_port(*args, **kwargs):
        return (None, None)

    async def mock_get_ingress_host_port(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "apolo_app_types.outputs.utils.apolo_secrets.create_apolo_secret",
        create_apolo_secret,
    )
    monkeypatch.setattr(
        "apolo_apps_launchpad.outputs_processor.get_service_host_port",
        mock_get_service_host_port,
    )
    monkeypatch.setattr(
        "apolo_apps_launchpad.outputs_processor.get_ingress_host_port",
        mock_get_ingress_host_port,
    )

    res = await get_launchpad_outputs(
        helm_values={
            "LAUNCHPAD_INITIAL_CONFIG": {
                "vllm": {
                    "hugging_face_model": {
                        "model_hf_name": "meta-llama/Llama-3.1-8B-Instruct"
                    },
                    "preset": {"name": "gpu-small"},
                }
            },
            **KEYCLOAK_HELM_VALUES,
        },
        app_instance_id=app_instance_id,
    )

    assert res
    assert "app_url" in res

    app_url = res["app_url"]
    assert app_url["internal_url"] is None
    assert app_url["external_url"] is None
    assert res["keycloak_config"]["auth_admin_password"]["__type__"] == "ApoloSecret"


@pytest.mark.asyncio
async def test_launchpad_output_generation_custom_ports(
    setup_clients, mock_kubernetes_client, app_instance_id, monkeypatch
):
    """Test launchpad output generation with custom ports."""

    async def mock_get_service_host_port(*args, **kwargs):
        return ("launchpad-service.namespace", 8080)

    async def mock_get_ingress_host_port(*args, **kwargs):
        return ("launchpad.custom.domain", 443)

    monkeypatch.setattr(
        "apolo_app_types.outputs.utils.apolo_secrets.create_apolo_secret",
        create_apolo_secret,
    )
    monkeypatch.setattr(
        "apolo_apps_launchpad.outputs_processor.get_service_host_port",
        mock_get_service_host_port,
    )
    monkeypatch.setattr(
        "apolo_apps_launchpad.outputs_processor.get_ingress_host_port",
        mock_get_ingress_host_port,
    )

    res = await get_launchpad_outputs(
        helm_values={
            "LAUNCHPAD_INITIAL_CONFIG": {
                "vllm": {
                    "hugging_face_model": {
                        "model_hf_name": "meta-llama/Llama-3.1-8B-Instruct"
                    },
                    "preset": {"name": "gpu-large"},
                }
            },
            **KEYCLOAK_HELM_VALUES,
        },
        app_instance_id=app_instance_id,
    )

    assert res
    assert "app_url" in res

    app_url = res["app_url"]
    assert app_url["internal_url"] == {
        "__type__": "WebApp",
        "api_type": "webapp",
        "base_path": "/",
        "host": "launchpad-service.namespace",
        "port": 8080,
        "protocol": "http",
        "timeout": 30.0,
    }
    assert app_url["external_url"] == {
        "__type__": "WebApp",
        "api_type": "webapp",
        "base_path": "/",
        "host": "launchpad.custom.domain",
        "port": 443,
        "protocol": "https",
        "timeout": 30.0,
    }
