"""Verify explicit Procore configuration and migration isolation."""

import json
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
from apolo_sdk import Client


@pytest.mark.parametrize("enabled", [None, True, False])
async def test_procore_input_preserves_the_three_states(
    apolo_client: Client, enabled: bool | None
) -> None:
    values = await LaunchpadInputsProcessor(client=apolo_client).gen_extra_values(
        input_=LaunchpadAppInputs(
            launchpad_web_app_config=LaunchpadWebAppConfig(
                preset=Preset(name="cpu-small")
            ),
            apps_config=AppsConfig(
                quick_start_config=NoQuickStartConfig(no_quickstart=True)
            ),
            procore_automatic_linking=enabled,
        ),
        app_name="test",
        namespace="platform",
        app_secrets_name="test-secrets",
        app_id="test-app",
    )
    assert values["procoreAutomaticLinking"] is enabled


@pytest.mark.parametrize("enabled", [None, True, False])
def test_procore_chart_is_opt_in_and_mounts_only_keycloak_credentials(
    tmp_path: Path, enabled: bool | None
) -> None:
    root = Path(__file__).resolve().parents[3]
    values = tmp_path / "values.yaml"
    values.write_text(
        yaml.safe_dump(
            {
                "apolo_app_id": "test-app",
                "LAUNCHPAD_ADMIN_PASSWORD": "test-admin",
                "dbPassword": "test-db",
                "authResponseHeaders": ["X-Auth-Request-Email"],
                "procoreAutomaticLinking": enabled,
                "image": {"digest": "sha256:" + "a" * 64},
            }
        )
    )
    rendered = subprocess.check_output(
        ["helm", "template", "test", str(root / "charts/launchpad"), "-f", str(values)],
        text=True,
    )
    resources = [item for item in yaml.safe_load_all(rendered) if item]
    definition = json.loads(
        (root / "charts/launchpad/files/procore-auto-link.json").read_text()
    )
    realm_config = next(
        item
        for item in resources
        if item["kind"] == "ConfigMap" and "realm.json" in item.get("data", {})
    )
    realm = json.loads(realm_config["data"]["realm.json"])
    assert definition in realm["authenticationFlows"]
    assert realm["identityProviders"] == []
    assert realm["firstBrokerLoginFlow"] == "first broker login"
    jobs = [
        item
        for item in resources
        if item["kind"] == "Job"
        and item["metadata"]["name"].endswith("-procore-linking")
    ]
    if enabled is None:
        assert jobs == []
        return
    (job,) = jobs
    assert job["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "3"
    assert job["spec"]["activeDeadlineSeconds"] == 180
    pod = job["spec"]["template"]["spec"]
    assert pod["automountServiceAccountToken"] is False
    (container,) = pod["containers"]
    assert container["image"].endswith("@sha256:" + "a" * 64)
    assert container["args"][-2:] == ["--enable" if enabled else "--disable", "--apply"]
    assert "env" not in container
    assert "envFrom" not in container
    secrets = [volume["secret"] for volume in pod["volumes"] if "secret" in volume]
    assert secrets == [
        {
            "secretName": "launchpad-keycloak",
            "defaultMode": 0o440,
            "items": [{"key": "admin-password", "path": "admin-password"}],
        }
    ]
    flow_config = next(
        item
        for item in resources
        if item["kind"] == "ConfigMap" and "flow.json" in item.get("data", {})
    )
    assert json.loads(flow_config["data"]["flow.json"]) == definition
