"""Verify frontend migration values and rendered App ownership."""

import subprocess
from functools import partial
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
import yaml
from apolo_app_types.outputs.utils.apolo_secrets import create_apolo_secret_with_retry
from apolo_app_types.protocols.common import Preset
from apolo_apps_launchpad.inputs_processor import LaunchpadInputsProcessor
from apolo_apps_launchpad.types import (
    AppsConfig,
    LaunchpadAppInputs,
    LaunchpadWebAppConfig,
    NoQuickStartConfig,
)
from apolo_sdk import Client, ResourceNotFound


async def frontend_values(client: Client) -> dict[str, object]:
    return await LaunchpadInputsProcessor(client=client).gen_extra_values(
        input_=LaunchpadAppInputs(
            launchpad_web_app_config=LaunchpadWebAppConfig(
                preset=Preset(name="cpu-small")
            ),
            apps_config=AppsConfig(
                quick_start_config=NoQuickStartConfig(no_quickstart=True)
            ),
        ),
        app_name="frontend-test",
        namespace="platform",
        app_secrets_name="test-secrets",
        app_id="test-app",
    )


async def test_frontend_reuses_the_persisted_session_secret(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRONTEND_IMAGE_DIGEST", "sha256:" + "a" * 64)
    writer = AsyncMock()
    monkeypatch.setattr(apolo_client.secrets, "add", writer)
    first = await frontend_values(apolo_client)
    second = await frontend_values(apolo_client)
    assert (
        first["frontend"]
        == second["frontend"]
        == {
            "image": {"digest": "sha256:" + "a" * 64},
            "sessionSecret": "launchpad-frontend-session-test-app-value",
        }
    )
    writer.assert_not_awaited()


async def test_frontend_reconfiguration_reuses_the_secret_after_installation_failure(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRONTEND_IMAGE_DIGEST", "sha256:" + "a" * 64)
    original = apolo_client.secrets.get
    stored: dict[str, bytes] = {}

    async def get_secret(key: str) -> bytes:
        if key == "launchpad-frontend-session-test-app":
            if key not in stored:
                raise ResourceNotFound("The frontend secret does not exist.")
            return stored[key]
        return await original(key)

    async def add_secret(key: str, value: bytes) -> None:
        stored[key] = value

    writer = AsyncMock(side_effect=add_secret)
    generator = Mock(return_value="test-session-" * 6)
    monkeypatch.setattr(apolo_client.secrets, "get", get_secret)
    monkeypatch.setattr(apolo_client.secrets, "add", writer)
    monkeypatch.setattr(
        "apolo_apps_launchpad.inputs_processor.secrets.token_urlsafe", generator
    )
    first = await frontend_values(apolo_client)
    frontend = first["frontend"]
    assert isinstance(frontend, dict)
    secret = frontend["sessionSecret"]
    assert isinstance(secret, str)
    assert stored["launchpad-frontend-session-test-app"] == secret.encode()

    # The deployment fails before output processing can run.
    second = await frontend_values(apolo_client)
    assert first["frontend"] == second["frontend"]
    writer.assert_awaited_once_with(
        key="launchpad-frontend-session-test-app", value=secret.encode()
    )
    generator.assert_called_once_with(48)


async def test_frontend_stops_when_the_session_secret_cannot_be_persisted(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRONTEND_IMAGE_DIGEST", "sha256:" + "a" * 64)
    original = apolo_client.secrets.get

    async def get_secret(key: str) -> bytes:
        if key == "launchpad-frontend-session-test-app":
            raise ResourceNotFound("The frontend secret does not exist.")
        return await original(key)

    writer = AsyncMock(side_effect=RuntimeError("Secret storage is unavailable."))
    monkeypatch.setattr(
        "apolo_apps_launchpad.inputs_processor.create_apolo_secret_with_retry",
        partial(create_apolo_secret_with_retry, base_delay_seconds=0),
    )
    monkeypatch.setattr(apolo_client.secrets, "get", get_secret)
    monkeypatch.setattr(apolo_client.secrets, "add", writer)
    with pytest.raises(RuntimeError, match="Secret storage is unavailable"):
        await frontend_values(apolo_client)
    assert writer.await_count == 5


async def test_frontend_rejects_a_mutable_image(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRONTEND_IMAGE_DIGEST", "latest")
    with pytest.raises(ValueError, match="immutable SHA-256"):
        await frontend_values(apolo_client)


def test_frontend_chart_replaces_only_its_own_route(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    values = tmp_path / "frontend.yaml"
    values.write_text(
        yaml.safe_dump(
            {
                "apolo_app_id": "test-app",
                "LAUNCHPAD_ADMIN_PASSWORD": "test-admin",
                "dbPassword": "test-db",
                "authResponseHeaders": ["X-Auth-Request-Email"],
                "frontend": {
                    "image": {"digest": "sha256:" + "a" * 64},
                    "sessionSecret": "test-session-" * 4,
                },
            }
        )
    )
    chart = root / "charts/launchpad"
    rendered = subprocess.check_output(
        ["helm", "template", "test", str(chart), "--values", str(values)], text=True
    )
    resources = [item for item in yaml.safe_load_all(rendered) if item]
    service = next(
        item
        for item in resources
        if item["kind"] == "Service"
        and item["metadata"]["name"] == "launchpad-test-app-client"
    )
    assert service["spec"]["type"] == "ClusterIP"
    assert "externalName" not in service["spec"]
    assert service["spec"]["ports"] == [
        {"port": 80, "targetPort": "http", "name": "http"}
    ]
    ingress = next(
        item
        for item in resources
        if item["kind"] == "Ingress"
        and item["metadata"]["name"] == "launchpad-test-app-client"
    )
    backend = ingress["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"]
    assert backend["port"]["name"] == "http"
    deployment = next(
        item
        for item in resources
        if item["kind"] == "Deployment"
        and item["metadata"]["name"] == "launchpad-test-app-client"
    )
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "ghcr.io/neuro-inc/launchpad-web-ui@sha256:" + "a" * 64
    assert [item["name"] for item in container["env"]] == [
        "NEXTAUTH_URL",
        "NEXTAUTH_SECRET",
    ]
    assert container["env"][0]["value"].startswith("https://launchpad-test-app.")
    assert not any(
        item["kind"] == "Job" and "netlify" in item["metadata"]["name"]
        for item in resources
    )


async def test_backend_digest_reaches_the_deployment_and_lifecycle_jobs(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    digest = "sha256:" + "b" * 64
    monkeypatch.setenv("APP_IMAGE_DIGEST", digest)
    monkeypatch.setenv("APP_IMAGE_TAG", "mutable-tag")
    monkeypatch.delenv("FRONTEND_IMAGE_DIGEST", raising=False)
    generated = await frontend_values(apolo_client)
    assert generated["image"] == {"tag": "mutable-tag", "digest": digest}
    values = tmp_path / "backend.yaml"
    values.write_text(
        yaml.safe_dump(
            {
                "image": generated["image"],
                "apolo_app_id": "test-app",
                "LAUNCHPAD_ADMIN_PASSWORD": "test-admin",
                "dbPassword": "test-db",
                "authResponseHeaders": ["X-Auth-Request-Email"],
            }
        )
    )
    chart = Path(__file__).resolve().parents[3] / "charts/launchpad"
    rendered = subprocess.check_output(
        ["helm", "template", "test", str(chart), "--values", str(values)], text=True
    )
    backend_resources = {
        "launchpad-test-app",
        "launchpad-test-app-cleanup-job",
        "launchpad-test-app-netlify-domain-job",
        "launchpad-test-app-netlify-cleanup-job",
    }
    images = {}
    for resource in yaml.safe_load_all(rendered):
        if not resource or resource["kind"] not in ("Deployment", "Job"):
            continue
        name = resource["metadata"]["name"]
        if name in backend_resources:
            images[name] = resource["spec"]["template"]["spec"]["containers"][0][
                "image"
            ]
    assert images == {
        name: "ghcr.io/neuro-inc/launchpad@" + digest for name in backend_resources
    }


async def test_backend_rejects_an_invalid_digest(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_IMAGE_DIGEST", "latest")
    with pytest.raises(
        ValueError, match="APP_IMAGE_DIGEST must be an immutable SHA-256"
    ):
        await frontend_values(apolo_client)
