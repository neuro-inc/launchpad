"""Verify frontend migration values and rendered App ownership."""

import subprocess
from pathlib import Path

import pytest
import yaml
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


async def test_frontend_generates_a_secret_when_it_is_absent(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRONTEND_IMAGE_DIGEST", "sha256:" + "a" * 64)
    original = apolo_client.secrets.get

    async def get_secret(key: str) -> bytes:
        if key == "launchpad-frontend-session-test-app":
            raise ResourceNotFound("The frontend secret does not exist.")
        return await original(key)

    monkeypatch.setattr(apolo_client.secrets, "get", get_secret)
    values = await frontend_values(apolo_client)
    frontend = values["frontend"]
    assert isinstance(frontend, dict)
    secret = frontend["sessionSecret"]
    assert isinstance(secret, str)
    assert len(secret) >= 32


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
