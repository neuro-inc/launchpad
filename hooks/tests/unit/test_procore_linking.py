"""Verify explicit Procore configuration and migration isolation."""

import json
from pathlib import Path

import pytest
from apolo_app_types import ApoloSecret
from apolo_app_types.protocols.common import Preset
from apolo_apps_launchpad.inputs_processor import LaunchpadInputsProcessor
from apolo_apps_launchpad.types import (
    AppsConfig,
    LaunchpadAppInputs,
    LaunchpadWebAppConfig,
    NoQuickStartConfig,
    ProcoreIdentityProviderConfig,
    ProcoreSettings,
)
from apolo_sdk import Client

from .chart_helpers import CHART, render_chart


def test_keycloak_upgrade_preserves_service_and_realm_contract(tmp_path: Path) -> None:
    name = "launchpad-test-app-keycloak"
    resources = render_chart(
        tmp_path,
        {
            "keycloak": {
                "fullnameOverride": name,
                "auth": {"adminPassword": "test-keycloak-admin"},
            },
            "keycloakRealmImportConfigMapName": f"{name}-realm",
            "procoreAutomaticLinking": False,
        },
    )
    indexed = {(item["kind"], item["metadata"]["name"]): item for item in resources}
    statefulset = indexed["StatefulSet", name]["spec"]
    selector = {
        "app.kubernetes.io/name": "keycloak",
        "app.kubernetes.io/instance": "test",
        "app.kubernetes.io/component": "keycloak",
    }
    assert statefulset["selector"]["matchLabels"] == selector
    assert statefulset["serviceName"] == f"{name}-headless"
    assert statefulset["podManagementPolicy"] == "Parallel"
    service = indexed["Service", name]
    assert service["metadata"]["labels"]["service"] == "keycloak"
    assert service["spec"]["selector"] == selector
    assert service["spec"]["ports"] == [
        {"name": "http", "port": 80, "targetPort": "http"}
    ]
    pod = statefulset["template"]["spec"]
    (keycloak,) = pod["containers"]
    assert keycloak["image"].startswith("quay.io/keycloak/keycloak:26.8.2-3@sha256:")
    assert keycloak["readinessProbe"]["httpGet"]["port"] == "management"
    assert {"name": "realm-import", "configMap": {"name": f"{name}-realm"}} in pod[
        "volumes"
    ]
    assert keycloak["securityContext"]["readOnlyRootFilesystem"] is True
    procore = indexed["Job", "launchpad-test-app-procore-linking"]["spec"]["template"][
        "spec"
    ]
    assert procore["containers"][0]["args"][:2] == ["--server", f"http://{name}:80"]
    password = next(
        entry
        for entry in keycloak["env"]
        if entry["name"] == "KC_BOOTSTRAP_ADMIN_PASSWORD"
    )
    assert password["valueFrom"]["secretKeyRef"] == {
        "name": name,
        "key": "admin-password",
    }
    assert (
        "checksum/keycloak-admin" in statefulset["template"]["metadata"]["annotations"]
    )


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
            procore_settings=ProcoreSettings(automatic_linking=enabled),
        ),
        app_name="test",
        namespace="platform",
        app_secrets_name="test-secrets",
        app_id="test-app",
    )
    assert values["procoreAutomaticLinking"] is enabled
    assert "procoreProvider" not in values


@pytest.mark.parametrize("enabled", [None, True, False])
def test_procore_chart_is_opt_in_and_mounts_only_keycloak_credentials(
    tmp_path: Path, enabled: bool | None
) -> None:
    resources = render_chart(
        tmp_path,
        {
            "procoreAutomaticLinking": enabled,
            "image": {"digest": "sha256:" + "a" * 64},
        },
    )
    definition = json.loads((CHART / "files/procore-auto-link.json").read_text())
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


async def test_provider_credentials_remain_a_namespaced_secret_reference(
    apolo_client: Client,
) -> None:
    inputs = LaunchpadAppInputs(
        launchpad_web_app_config=LaunchpadWebAppConfig(preset=Preset(name="cpu-small")),
        apps_config=AppsConfig(
            quick_start_config=NoQuickStartConfig(no_quickstart=True)
        ),
        procore_settings=ProcoreSettings(
            identity_provider=ProcoreIdentityProviderConfig(
                client_id="test-client",
                client_secret=ApoloSecret(key="PROCORE_CLIENT_SECRET"),
                environment="sandbox",
                trust_email=True,
            )
        ),
    )
    values = await LaunchpadInputsProcessor(client=apolo_client).gen_extra_values(
        input_=inputs,
        app_name="test",
        namespace="platform",
        app_secrets_name="project-test-secrets",
        app_id="test-app",
    )
    assert values["procoreProvider"] == {
        "clientId": "test-client",
        "environment": "sandbox",
        "enabled": True,
        "trustEmail": True,
        "clientSecret": {
            "valueFrom": {
                "secretKeyRef": {
                    "name": "project-test-secrets",
                    "key": "PROCORE_CLIENT_SECRET",
                }
            }
        },
    }


@pytest.mark.parametrize("linking", [None, True, False])
def test_provider_job_mounts_just_the_required_secret_key(
    tmp_path: Path, linking: bool | None
) -> None:
    provider = {
        "clientId": "test-client",
        "environment": "sandbox",
        "enabled": True,
        "trustEmail": False,
        "clientSecret": {
            "valueFrom": {
                "secretKeyRef": {
                    "name": "project-test-secrets",
                    "key": "PROCORE_CLIENT_SECRET",
                }
            }
        },
    }
    resources = render_chart(
        tmp_path,
        {
            "procoreProvider": provider,
            "procoreAutomaticLinking": linking,
        },
    )
    job = next(
        item
        for item in resources
        if item["kind"] == "Job"
        and item["metadata"]["name"].endswith("-procore-linking")
    )
    pod = job["spec"]["template"]["spec"]
    (container,) = pod["containers"]
    assert ("--enable" in container["args"]) is (linking is True)
    assert ("--disable" in container["args"]) is (linking is False)
    assert "--provider-file" in container["args"]
    assert "env" not in container
    secret = next(
        volume["secret"]
        for volume in pod["volumes"]
        if volume["name"] == "procore-client"
    )
    assert secret == {
        "secretName": "project-test-secrets",
        "defaultMode": 0o440,
        "items": [{"key": "PROCORE_CLIENT_SECRET", "path": "client-secret"}],
    }
    config = next(
        item
        for item in resources
        if item["kind"] == "ConfigMap" and "provider.json" in item.get("data", {})
    )
    projected = json.loads(config["data"]["provider.json"])
    assert projected == {
        key: value for key, value in provider.items() if key != "clientSecret"
    }
    for item in resources:
        if item["kind"] in ("Deployment", "StatefulSet"):
            assert "procore-client" not in json.dumps(item)
