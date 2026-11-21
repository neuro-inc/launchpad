from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from apolo_app_types.protocols.common import Preset
from apolo_apps_launchpad.inputs_processor import LaunchpadInputsProcessor
from apolo_apps_launchpad.types import (
    AppsConfig,
    LaunchpadAppInputs,
    LaunchpadWebAppConfig,
    NoQuickStartConfig,
)
from apolo_sdk import Client, ResourceNotFound

from .chart_helpers import render_chart


@pytest.mark.parametrize("shared", [True, False])
def test_database_wiring_for_shared_and_isolated_installs(
    tmp_path: Path, shared: bool
) -> None:
    manifests = render_chart(
        tmp_path,
        {
            "postgresql": {"enabled": shared},
            "isolatedDatabases": {
                "passwords": {
                    "launchpad": "launchpad-db-test",
                    "keycloak": "kc-db-test",
                },
            },
        },
    )
    resources = {(doc["kind"], doc["metadata"]["name"]): doc for doc in manifests}
    assert (("StatefulSet", "launchpad-db") in resources) is shared
    assert (("Secret", "launchpad-db-secret") in resources) is shared
    for app, kind, app_name, prefix in (
        ("launchpad", "Deployment", "launchpad-test-app", "DB_"),
        ("keycloak", "StatefulSet", "launchpad-keycloak", "KC_DB_"),
    ):
        service = f"launchpad-test-app-{app}-db"
        assert (("StatefulSet", service) in resources) is (not shared)
        if not shared:
            db = resources["StatefulSet", service]["spec"]
            assert db["volumeClaimTemplates"][0]["spec"]["accessModes"] == [
                "ReadWriteOnce"
            ]
            secret = resources["Secret", f"{service}-secret"]["stringData"]
            assert secret["DB_USER"] == secret["DB_NAME"] == app
            db_policy = resources["NetworkPolicy", service]["spec"]["ingress"]
            allowed = db_policy[0]["from"][0]["podSelector"]["matchLabels"]
            app_labels = resources[kind, app_name]["spec"]["template"]["metadata"][
                "labels"
            ]
            assert all(app_labels[key] == value for key, value in allowed.items())
        pod = resources[kind, app_name]["spec"]["template"]["spec"]
        env = {entry["name"]: entry for entry in pod["containers"][0]["env"]}
        user = "USER" if app == "launchpad" else "USERNAME"
        assert env[f"{prefix}{user}"]["value"] == ("postgres" if shared else app)
        secret_ref = env[f"{prefix}PASSWORD"]["valueFrom"]["secretKeyRef"]
        assert secret_ref == {
            "name": "launchpad-db-secret" if shared else f"{service}-secret",
            "key": "DB_PASSWORD",
        }


@pytest.mark.parametrize("installation", ["fresh", "legacy", "missing-legacy-password"])
async def test_installer_selects_databases_from_saved_credentials(
    apolo_client: Client, monkeypatch: pytest.MonkeyPatch, installation: str
) -> None:
    stored = {}
    if installation != "fresh":
        stored["launchpad-admin-pswd-test-app"] = b"existing-admin"
    if installation == "legacy":
        stored["keycloak-db-pswd-test-app"] = b"shared-password"
        stored["keycloak-isolated-db-pswd-test-app"] = b"unused-isolated-password"

    async def get(key: str) -> bytes:
        if key not in stored:
            raise ResourceNotFound("Test secret is missing")
        return stored[key]

    async def add(key: str, value: bytes) -> None:
        stored[key] = value

    writer = AsyncMock(side_effect=add)
    monkeypatch.setattr(apolo_client.secrets, "get", get)
    monkeypatch.setattr(apolo_client.secrets, "add", writer)
    monkeypatch.delenv("FRONTEND_IMAGE_DIGEST", raising=False)
    processor = LaunchpadInputsProcessor(apolo_client)

    async def values() -> dict[str, Any]:
        return await processor.gen_extra_values(
            input_=LaunchpadAppInputs(
                launchpad_web_app_config=LaunchpadWebAppConfig(
                    preset=Preset(name="cpu-small")
                ),
                apps_config=AppsConfig(
                    quick_start_config=NoQuickStartConfig(no_quickstart=True)
                ),
            ),
            app_name="test",
            namespace="platform",
            app_secrets_name="test-secrets",
            app_id="test-app",
        )

    if installation == "missing-legacy-password":
        with pytest.raises(
            ValueError, match="Recover the saved PostgreSQL credentials"
        ):
            await values()
        writer.assert_not_awaited()
        return

    first = await values()
    if installation == "legacy":
        assert first["dbPassword"] == "shared-password"
        assert first["postgresql"].get("enabled", True)
        assert first["postgresql"]["fullnameOverride"] == "launchpad-test-app-db"
        assert first["dbSecretName"] == "launchpad-test-app-db-secret"
        assert "isolatedDatabases" not in first
        writer.assert_not_awaited()
        return

    stored["launchpad-admin-pswd-test-app"] = b"existing-admin"
    second = await values()
    assert second["postgresql"]["enabled"] is False
    assert "dbPassword" not in second
    passwords = first["isolatedDatabases"]["passwords"]
    assert passwords == second["isolatedDatabases"]["passwords"]
    assert passwords["launchpad"] != passwords["keycloak"]
    assert writer.await_count == 2
