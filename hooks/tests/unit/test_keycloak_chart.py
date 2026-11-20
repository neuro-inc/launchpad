import subprocess
from pathlib import Path

import pytest

from .chart_helpers import render_chart


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
