from pathlib import Path
from subprocess import CalledProcessError

import pytest

from .chart_helpers import render_chart


@pytest.mark.parametrize("shared", [True, False])
def test_database_wiring_for_shared_and_isolated_installs(
    tmp_path: Path, shared: bool
) -> None:
    app_id = "01234567-89ab-cdef-0123-456789abcdef"
    names = {"launchpad": "test-lp-db", "keycloak": "test-kc-db"}
    manifests = render_chart(
        tmp_path,
        {
            "apolo_app_id": app_id,
            "postgresql": {"enabled": shared},
            "isolatedDatabases": {
                "enabled": not shared,
                "names": names,
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
        ("launchpad", "Deployment", f"launchpad-{app_id}", "DB_"),
        ("keycloak", "StatefulSet", "launchpad-keycloak", "KC_DB_"),
    ):
        service = names[app]
        assert (("StatefulSet", service) in resources) is (not shared)
        if not shared:
            db = resources["StatefulSet", service]["spec"]
            assert db["serviceName"] == service
            assert ("Service", service) in resources
            assert db["volumeClaimTemplates"][0]["spec"]["accessModes"] == [
                "ReadWriteOnce"
            ]
            secret = resources["Secret", f"{service}-secret"]["stringData"]
            assert secret["DB_HOST"] == service
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
        if app == "launchpad":
            assert env["DB_HOST"]["value"] == ("launchpad-db" if shared else service)
        else:
            assert env["KC_DB_URL_HOST"]["valueFrom"]["secretKeyRef"] == {
                "name": secret_ref["name"],
                "key": "DB_HOST",
            }


def test_external_databases_render_connection_references_only(tmp_path: Path) -> None:
    manifests = render_chart(
        tmp_path,
        {
            "postgresql": {"enabled": False},
            "externalDatabase": {"existingSecret": "launchpad-external-db"},
            "keycloak": {
                "auth": {"adminPassword": "test-keycloak-admin"},
                "externalDatabase": {
                    "existingSecret": "keycloak-external-db",
                    "user": "keycloak_owner",
                    "database": "keycloak_external",
                    "port": 5433,
                },
            },
        },
    )
    resources = {(doc["kind"], doc["metadata"]["name"]): doc for doc in manifests}
    assert [name for kind, name in resources if kind == "StatefulSet"] == [
        "launchpad-keycloak"
    ]
    assert not any(kind == "Secret" and "db" in name for kind, name in resources)
    launchpad = resources["Deployment", "launchpad-test-app"]
    keycloak = resources["StatefulSet", "launchpad-keycloak"]
    launchpad_env = {
        entry["name"]: entry
        for entry in launchpad["spec"]["template"]["spec"]["containers"][0]["env"]
    }
    keycloak_env = {
        entry["name"]: entry
        for entry in keycloak["spec"]["template"]["spec"]["containers"][0]["env"]
    }
    for key in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        assert launchpad_env[key]["valueFrom"]["secretKeyRef"] == {
            "name": "launchpad-external-db",
            "key": key,
        }
    for env_name, key in (
        ("KC_DB_URL_HOST", "DB_HOST"),
        ("KC_DB_PASSWORD", "DB_PASSWORD"),
    ):
        assert keycloak_env[env_name]["valueFrom"]["secretKeyRef"] == {
            "name": "keycloak-external-db",
            "key": key,
        }
    assert keycloak_env["KC_DB_URL_DATABASE"]["value"] == "keycloak_external"
    assert keycloak_env["KC_DB_USERNAME"]["value"] == "keycloak_owner"
    assert keycloak_env["KC_DB_URL_PORT"]["value"] == "5433"


def test_chart_rejects_both_bundled_database_modes(tmp_path: Path) -> None:
    with pytest.raises(CalledProcessError) as error:
        render_chart(tmp_path, {"isolatedDatabases": {"enabled": True}})
    assert "Enable only one bundled PostgreSQL option." in error.value.stderr
