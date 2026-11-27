import subprocess
from pathlib import Path

import pytest

from .chart_helpers import render_chart


def test_keycloak_preserves_headless_service_name_and_configures_theme(
    tmp_path: Path,
) -> None:
    name = "launchpad-01234567-89ab-cdef-0123-456789abcdef-keycloak"
    resources = render_chart(
        tmp_path,
        {
            "keycloak": {
                "fullnameOverride": name,
                "auth": {"adminPassword": "test-keycloak-admin"},
                "theme": {"revision": "test-revision", "path": "kc-theme/apolo"},
            },
        },
    )
    headless_name = f"{name}-headles"
    assert any(
        item["kind"] == "Service" and item["metadata"]["name"] == headless_name
        for item in resources
    )
    statefulset = next(
        item["spec"]
        for item in resources
        if item["kind"] == "StatefulSet" and item["metadata"]["name"] == name
    )
    assert statefulset["serviceName"] == headless_name
    pod = statefulset["template"]["spec"]
    assert pod["containers"][0]["args"] == ["start", "--import-realm"]
    theme = next(
        init for init in pod["initContainers"] if init["name"] == "fetch-theme"
    )
    assert {env["name"]: env["value"] for env in theme["env"]} == {
        "THEME_REPOSITORY": "https://github.com/neuro-inc/launchpad.git",
        "THEME_REVISION": "test-revision",
        "THEME_PATH": "kc-theme/apolo",
    }


def test_keycloak_bootstrap_requires_a_password_or_existing_secret(
    tmp_path: Path,
) -> None:
    with pytest.raises(subprocess.CalledProcessError) as error:
        render_chart(tmp_path, {"keycloak": {}})
    assert (
        "Set keycloak.auth.adminPassword or keycloak.auth.existingSecret"
        in error.value.stderr
    )

    resources = render_chart(
        tmp_path,
        {"keycloak": {"auth": {"existingSecret": "test-keycloak-credentials"}}},
    )
    assert not any(
        item["kind"] == "Secret" and item["metadata"]["name"] == "launchpad-keycloak"
        for item in resources
    )
    statefulset = next(
        item
        for item in resources
        if item["kind"] == "StatefulSet"
        and item["metadata"]["name"] == "launchpad-keycloak"
    )
    (container,) = statefulset["spec"]["template"]["spec"]["containers"]
    password = next(
        entry
        for entry in container["env"]
        if entry["name"] == "KC_BOOTSTRAP_ADMIN_PASSWORD"
    )
    assert password["valueFrom"]["secretKeyRef"]["name"] == "test-keycloak-credentials"
