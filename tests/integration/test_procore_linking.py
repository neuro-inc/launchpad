"""Exercise migration against the same Keycloak version as the chart."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from keycloak import KeycloakAdmin
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from scripts.keycloak.procore_linking import (
    FLOW_ALIAS,
    FlowDefinition,
    ProcoreProviderSettings,
    reconcile,
)


@pytest.fixture(scope="module")
def keycloak_admin() -> Iterator[KeycloakAdmin]:
    with (
        DockerContainer("quay.io/keycloak/keycloak:26.3.0")
        .with_env("KC_BOOTSTRAP_ADMIN_USERNAME", "test-admin")
        .with_env("KC_BOOTSTRAP_ADMIN_PASSWORD", "test-password")
        .with_exposed_ports(8080)
        .with_command("start-dev")
        .waiting_for(LogMessageWaitStrategy("Listening on:").with_startup_timeout(180))
    ) as container:
        admin = KeycloakAdmin(
            server_url=f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}/",
            username="test-admin",
            password="test-password",
            realm_name="master",
            timeout=20,
        )
        yield admin


def account_snapshot(
    admin: KeycloakAdmin, user_id: str, client_id: str
) -> dict[str, object]:
    return {
        "user": admin.get_user(user_id),
        "direct_roles": admin.get_realm_roles_of_user(user_id),
        "groups": admin.get_user_groups(user_id),
        "inherited_roles": admin.get_composite_realm_roles_of_user(user_id),
        "client_roles": admin.get_client_roles_of_user(user_id, client_id),
    }


def test_migration_preserves_existing_accounts_roles_groups_and_provider_settings(
    keycloak_admin: KeycloakAdmin,
) -> None:
    definition = FlowDefinition.model_validate_json(
        (
            Path(__file__).parents[2] / "charts/launchpad/files/procore-auto-link.json"
        ).read_text()
    )
    admin = keycloak_admin
    admin.change_current_realm("master")
    admin.create_realm({"realm": "launchpad", "enabled": True})
    admin.change_current_realm("launchpad")
    for alias in ("procore", "unrelated"):
        admin.create_idp(
            {
                "alias": alias,
                "providerId": "oidc",
                "enabled": True,
                "trustEmail": True,
                "config": {
                    "clientId": "test-client",
                    "clientSecret": "test-secret",
                    "syncMode": "LEGACY",
                },
            }
        )
    admin.create_realm_role({"name": "reviewer"})
    admin.create_realm_role({"name": "launchpad-admin"})
    group_id = admin.create_group({"name": "reviewers"})
    assert group_id is not None
    admin.assign_group_realm_roles(group_id, [admin.get_realm_role("reviewer")])
    client_id = admin.create_client({"clientId": "launchpad-test"})
    admin.create_client_role(client_id, {"name": "manage-apps"})
    user_ids = []
    for role in ("reviewer", "launchpad-admin"):
        user_id = admin.create_user(
            {
                "username": f"{role}@example.test",
                "email": f"{role}@example.test",
                "enabled": True,
                "emailVerified": False,
            }
        )
        admin.assign_realm_roles(user_id, [admin.get_realm_role(role)])
        admin.group_user_add(user_id, group_id)
        admin.assign_client_role(
            user_id, client_id, [admin.get_client_role(client_id, "manage-apps")]
        )
        user_ids.append(user_id)
    before = {
        user_id: account_snapshot(admin, user_id, client_id) for user_id in user_ids
    }
    provider = admin.get_idp("procore")
    unrelated = admin.get_idp("unrelated")
    realm = admin.get_realm("launchpad")
    reconcile(admin, definition, enabled=True)
    assert admin.get_idp("procore") == provider
    for _ in range(2):
        reconcile(admin, definition, enabled=True, apply=True)
        assert admin.get_idp("procore") == {
            **provider,
            "firstBrokerLoginFlowAlias": FLOW_ALIAS,
        }
        for user_id in user_ids:
            assert account_snapshot(admin, user_id, client_id) == before[user_id]
        assert admin.get_idp("unrelated") == unrelated
        assert admin.get_realm("launchpad") == realm
    reconcile(admin, definition, enabled=False, apply=True)
    assert admin.get_idp("procore") == provider
    assert len(admin.get_users()) == len(user_ids)
    for user_id in user_ids:
        assert account_snapshot(admin, user_id, client_id) == before[user_id]

    # Fresh realms import the same inactive definition before provider configuration.
    admin.change_current_realm("master")
    admin.create_realm(
        {
            "realm": "fresh",
            "enabled": True,
            "authenticationFlows": [definition.model_dump()],
        }
    )
    admin.change_current_realm("fresh")
    assert admin.get_realm("fresh")["firstBrokerLoginFlow"] == "first broker login"
    assert admin.get_idps() == []
    admin.create_idp(
        {
            "alias": "procore",
            "providerId": "oidc",
            "enabled": True,
            "trustEmail": True,
            "config": {"clientId": "test-client"},
        }
    )
    reconcile(admin, definition, enabled=True, apply=True)
    assert admin.get_idp("procore")["firstBrokerLoginFlowAlias"] == FLOW_ALIAS


def test_provider_creation_and_secret_rotation_preserve_existing_permissions(
    keycloak_admin: KeycloakAdmin,
) -> None:
    admin = keycloak_admin
    admin.change_current_realm("master")
    admin.create_realm({"realm": "configured-procore", "enabled": True})
    admin.change_current_realm("configured-procore")
    admin.create_realm_role({"name": "reviewer"})
    group_id = admin.create_group({"name": "reviewers"})
    assert group_id is not None
    user_id = admin.create_user(
        {
            "username": "reviewer@example.test",
            "email": "reviewer@example.test",
            "enabled": True,
        }
    )
    admin.group_user_add(user_id, group_id)
    admin.assign_group_realm_roles(group_id, [admin.get_realm_role("reviewer")])
    client_id = admin.create_client({"clientId": "permission-test"})
    realm = admin.get_realm("configured-procore")
    admin.create_idp(
        {
            "alias": "unrelated",
            "providerId": "oidc",
            "enabled": True,
            "config": {"clientId": "unrelated-client"},
        }
    )
    unrelated = admin.get_idp("unrelated")
    before = account_snapshot(admin, user_id, client_id)
    definition = FlowDefinition.model_validate_json(
        (
            Path(__file__).parents[2] / "charts/launchpad/files/procore-auto-link.json"
        ).read_text()
    )
    settings = ProcoreProviderSettings(clientId="test-client", environment="sandbox")
    reconcile(
        admin,
        definition,
        enabled=None,
        apply=True,
        settings=settings,
        client_secret="test",
    )
    provider = admin.get_idp("procore")
    assert provider["providerId"] == "oauth2"
    assert provider["trustEmail"] is False
    assert provider["config"]["userIDClaim"] == "id"
    assert (
        provider["config"]["userInfoUrl"] == "https://sandbox.procore.com/rest/v1.0/me"
    )
    assert provider.get("firstBrokerLoginFlowAlias", "") == ""
    assert not any(
        flow["alias"] == FLOW_ALIAS for flow in admin.get_authentication_flows()
    )
    settings = settings.model_copy(update={"trustEmail": True})
    for secret in ("test", "rotated-test", "rotated-test"):
        reconcile(
            admin,
            definition,
            enabled=True,
            apply=True,
            settings=settings,
            client_secret=secret,
        )
        assert admin.get_idp("procore")["firstBrokerLoginFlowAlias"] == FLOW_ALIAS
        assert account_snapshot(admin, user_id, client_id) == before
        assert admin.get_idp("unrelated") == unrelated
        assert admin.get_realm("configured-procore") == realm
    reconcile(
        admin,
        definition,
        enabled=False,
        apply=True,
        settings=settings.model_copy(update={"trustEmail": False}),
        client_secret="rotated-test",
    )
    assert admin.get_idp("procore").get("firstBrokerLoginFlowAlias", "") == ""
    assert admin.get_idp("procore")["trustEmail"] is False
    assert account_snapshot(admin, user_id, client_id) == before
