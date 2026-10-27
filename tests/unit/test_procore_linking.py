import copy
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakGetError

from scripts.keycloak import procore_linking
from scripts.keycloak.procore_linking import (
    FLOW_ALIAS,
    PROVIDERS,
    FlowDefinition,
    MigrationConflict,
    reconcile,
)


@pytest.fixture
def definition() -> FlowDefinition:
    path = Path(__file__).parents[2] / "charts/launchpad/files/procore-auto-link.json"
    return FlowDefinition.model_validate_json(path.read_text())


@pytest.fixture
def admin() -> Mock:
    client = Mock(spec=KeycloakAdmin)
    provider = {
        "alias": "procore",
        "providerId": "oauth2",
        "enabled": True,
        "trustEmail": True,
        "firstBrokerLoginFlowAlias": "",
        "config": {"clientSecret": "test-secret", "syncMode": "LEGACY"},
    }
    flows: list[dict[str, object]] = []
    executions: list[dict[str, object]] = []
    client.get_idps.return_value = []
    client.get_realm.return_value = {"firstBrokerLoginFlow": "first broker login"}
    client.connection = Mock(realm_name="launchpad")
    client.provider = provider
    client.flows = flows
    client.executions = executions
    client.get_idp.side_effect = lambda alias: copy.deepcopy(provider)
    client.get_authentication_flows.side_effect = lambda: copy.deepcopy(flows)
    client.get_authentication_flow_executions.side_effect = lambda alias: copy.deepcopy(
        executions
    )
    client.get_authentication_flow_execution.return_value = {
        "authenticatorConfig": None
    }
    client.create_authentication_flow.side_effect = lambda payload: flows.append(
        copy.deepcopy(payload)
    )

    def create_execution(payload: dict[str, object], flow_alias: str) -> None:
        assert flow_alias == FLOW_ALIAS
        executions.append(
            {
                "id": str(len(executions)),
                "providerId": payload["provider"],
                "requirement": "DISABLED",
            }
        )

    def update_execution(payload: dict[str, object], flow_alias: str) -> None:
        assert flow_alias == FLOW_ALIAS
        next(step for step in executions if step["id"] == payload["id"]).update(payload)

    def update_provider(alias: str, payload: dict[str, object]) -> None:
        assert alias == "procore"
        provider.clear()
        provider.update(copy.deepcopy(payload))

    client.create_authentication_flow_execution.side_effect = create_execution
    client.update_authentication_flow_executions.side_effect = update_execution
    client.update_idp.side_effect = update_provider
    return client


def writes(admin: Mock) -> list[str]:
    return [
        call[0]
        for call in admin.mock_calls
        if call[0].startswith(("create_", "update_", "delete_", "assign_", "add_"))
    ]


def test_enable_is_idempotent_and_only_changes_the_procore_binding(
    admin: Mock, definition: FlowDefinition
) -> None:
    before = copy.deepcopy(admin.provider)
    reconcile(admin, definition, enabled=True, apply=True)
    assert admin.provider == {**before, "firstBrokerLoginFlowAlias": FLOW_ALIAS}
    assert tuple(step["providerId"] for step in admin.executions) == PROVIDERS
    assert all(step["requirement"] == "ALTERNATIVE" for step in admin.executions)
    first_writes = writes(admin)
    reconcile(admin, definition, enabled=True, apply=True)
    assert writes(admin) == first_writes
    assert set(first_writes) == {
        "create_authentication_flow",
        "create_authentication_flow_execution",
        "update_authentication_flow_executions",
        "update_idp",
    }
    assert {call.args[0] for call in admin.get_idp.call_args_list} == {"procore"}


def test_dry_run_does_not_write(admin: Mock, definition: FlowDefinition) -> None:
    reconcile(admin, definition, enabled=True)
    assert writes(admin) == []


def test_disable_preserves_provider_configuration_and_flow(
    admin: Mock, definition: FlowDefinition
) -> None:
    reconcile(admin, definition, enabled=True, apply=True)
    before = copy.deepcopy(admin.provider)
    admin.reset_mock()
    reconcile(admin, definition, enabled=False, apply=True)
    assert admin.provider == {**before, "firstBrokerLoginFlowAlias": ""}
    assert writes(admin) == ["update_idp"]
    reconcile(admin, definition, enabled=False, apply=True)
    assert writes(admin) == ["update_idp"]


@pytest.mark.parametrize("enabled", [True, False])
def test_refuses_a_custom_provider_binding(
    admin: Mock, definition: FlowDefinition, enabled: bool
) -> None:
    admin.provider["firstBrokerLoginFlowAlias"] = "customer-custom-login"
    with pytest.raises(MigrationConflict, match="custom first-login"):
        reconcile(admin, definition, enabled=enabled, apply=True)
    assert writes(admin) == []


def test_missing_provider_fails_without_creating_a_flow(
    admin: Mock, definition: FlowDefinition
) -> None:
    admin.get_idp.side_effect = KeycloakGetError(response_code=404)
    with pytest.raises(MigrationConflict, match="Configure the Procore provider"):
        reconcile(admin, definition, enabled=True, apply=True)
    reconcile(admin, definition, enabled=False, apply=True)
    assert writes(admin) == []


def test_requires_trusted_email_claims(admin: Mock, definition: FlowDefinition) -> None:
    admin.provider["trustEmail"] = False
    with pytest.raises(MigrationConflict, match="trust its email"):
        reconcile(admin, definition, enabled=True, apply=True)
    assert writes(admin) == []


def test_resumes_a_partial_owned_flow(admin: Mock, definition: FlowDefinition) -> None:
    admin.flows.append(definition.model_dump(exclude={"authenticationExecutions"}))
    admin.executions.append(
        {"id": "0", "providerId": PROVIDERS[0], "requirement": "DISABLED"}
    )
    reconcile(admin, definition, enabled=True, apply=True)
    admin.create_authentication_flow.assert_not_called()
    assert len(admin.executions) == 2
    assert admin.provider["firstBrokerLoginFlowAlias"] == FLOW_ALIAS


@pytest.mark.parametrize("custom", ["extra-execution", "required", "execution-config"])
def test_refuses_custom_flow_executions(
    admin: Mock, definition: FlowDefinition, custom: str
) -> None:
    admin.flows.append(definition.model_dump(exclude={"authenticationExecutions"}))
    admin.executions.extend(
        {"id": str(i), "providerId": provider, "requirement": "ALTERNATIVE"}
        for i, provider in enumerate(PROVIDERS)
    )
    if custom == "extra-execution":
        admin.executions.append(
            {"id": "3", "providerId": "allow-access", "requirement": "ALTERNATIVE"}
        )
    elif custom == "required":
        admin.executions[0]["requirement"] = "REQUIRED"
    else:
        admin.get_authentication_flow_execution.return_value = {
            "authenticatorConfig": "customer-config"
        }
    with pytest.raises(MigrationConflict):
        reconcile(admin, definition, enabled=True, apply=True)
    assert writes(admin) == []


@pytest.mark.parametrize("with_provider", [False, True])
def test_cli_does_not_log_provider_error_bodies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    with_provider: bool,
) -> None:
    password = tmp_path / "password"
    password.write_text("synthetic-password")
    flow = Path(__file__).parents[2] / "charts/launchpad/files/procore-auto-link.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "migration",
            "--server",
            "https://keycloak.test",
            "--password-file",
            str(password),
            "--flow-file",
            str(flow),
            "--enable",
            "--apply",
        ],
    )
    if with_provider:
        configuration = tmp_path / "provider.json"
        configuration.write_text(
            procore_linking.ProcoreProviderSettings(
                clientId="test-client"
            ).model_dump_json()
        )
        secret = tmp_path / "client-secret"
        secret.write_text("synthetic-procore-secret")
        monkeypatch.setattr(
            "sys.argv",
            [
                *sys.argv,
                "--provider-file",
                str(configuration),
                "--client-secret-file",
                str(secret),
            ],
        )
    constructor = Mock(
        side_effect=KeycloakGetError(
            "synthetic-password", response_code=401, response_body=b"synthetic-token"
        )
    )
    monkeypatch.setattr(procore_linking, "KeycloakAdmin", constructor)
    assert procore_linking.main() == 1
    output = capsys.readouterr()
    assert "401" in output.err
    assert "synthetic-password" not in output.err + output.out
    assert "synthetic-token" not in output.err + output.out
    assert "synthetic-procore-secret" not in output.err + output.out


@pytest.mark.parametrize("requirement", ["ALTERNATIVE", "DISABLED"])
def test_only_adopts_a_complete_custom_flow_without_changes(
    admin: Mock, definition: FlowDefinition, requirement: str
) -> None:
    admin.flows.append(
        {
            **definition.model_dump(exclude={"authenticationExecutions"}),
            "description": "Manually configured",
        }
    )
    admin.executions.extend(
        {"id": str(i), "providerId": provider, "requirement": requirement}
        for i, provider in enumerate(PROVIDERS)
    )
    if requirement == "DISABLED":
        with pytest.raises(MigrationConflict, match="custom Procore flow"):
            reconcile(admin, definition, enabled=True, apply=True)
        assert writes(admin) == []
    else:
        reconcile(admin, definition, enabled=True, apply=True)
        assert writes(admin) == ["update_idp"]


def test_provider_drift_prevents_binding(
    admin: Mock, definition: FlowDefinition
) -> None:
    original = copy.deepcopy(admin.provider)
    admin.get_idp.side_effect = [original, {**original, "trustEmail": False}]
    with pytest.raises(MigrationConflict, match="changed during migration"):
        reconcile(admin, definition, enabled=True, apply=True)
    admin.update_idp.assert_not_called()


def test_interrupted_flow_creation_can_be_retried(
    admin: Mock, definition: FlowDefinition
) -> None:
    create_execution = admin.create_authentication_flow_execution.side_effect
    attempts = 0

    def interrupt(payload: dict[str, object], flow_alias: str) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise KeycloakGetError(response_code=503)
        create_execution(payload=payload, flow_alias=flow_alias)

    admin.create_authentication_flow_execution.side_effect = interrupt
    with pytest.raises(KeycloakGetError):
        reconcile(admin, definition, enabled=True, apply=True)
    admin.update_idp.assert_not_called()
    admin.create_authentication_flow_execution.side_effect = create_execution
    reconcile(admin, definition, enabled=True, apply=True)
    assert admin.provider["firstBrokerLoginFlowAlias"] == FLOW_ALIAS
    assert len(admin.executions) == 2


def test_rollback_accepts_keycloak_default_flow_normalization(
    admin: Mock, definition: FlowDefinition
) -> None:
    reconcile(admin, definition, enabled=True, apply=True)
    admin.get_realm.return_value = {"firstBrokerLoginFlow": "custom-realm-default"}
    update_provider = admin.update_idp.side_effect

    def normalize_default(alias: str, payload: dict[str, object]) -> None:
        update_provider(
            alias, {**payload, "firstBrokerLoginFlowAlias": "custom-realm-default"}
        )

    admin.update_idp.side_effect = normalize_default
    reconcile(admin, definition, enabled=False, apply=True)
    assert admin.provider["firstBrokerLoginFlowAlias"] == "custom-realm-default"
    assert admin.get_realm.call_args.args == ("launchpad",)


def test_provider_verification_rejects_unrelated_changes(
    admin: Mock, definition: FlowDefinition
) -> None:
    update_provider = admin.update_idp.side_effect

    def change_configuration(alias: str, payload: dict[str, object]) -> None:
        update_provider(alias, {**payload, "trustEmail": False})

    admin.update_idp.side_effect = change_configuration
    with pytest.raises(MigrationConflict, match="could not be verified"):
        reconcile(admin, definition, enabled=True, apply=True)


def test_rollback_accepts_an_omitted_default_binding(
    admin: Mock, definition: FlowDefinition
) -> None:
    reconcile(admin, definition, enabled=True, apply=True)
    update_provider = admin.update_idp.side_effect

    def omit_default(alias: str, payload: dict[str, object]) -> None:
        update_provider(
            alias,
            {
                key: value
                for key, value in payload.items()
                if key != "firstBrokerLoginFlowAlias"
            },
        )

    admin.update_idp.side_effect = omit_default
    reconcile(admin, definition, enabled=False, apply=True)
    assert "firstBrokerLoginFlowAlias" not in admin.provider


@pytest.mark.parametrize(
    "binding", ["realm", "other-first", "other-post", "procore-post"]
)
def test_refuses_to_repair_a_shared_flow(
    admin: Mock, definition: FlowDefinition, binding: str
) -> None:
    admin.flows.append(definition.model_dump(exclude={"authenticationExecutions"}))
    if binding == "realm":
        admin.get_realm.return_value["firstBrokerLoginFlow"] = FLOW_ALIAS
    else:
        admin.get_idps.return_value = [
            {
                "alias": "procore" if binding == "procore-post" else "unrelated",
                "firstBrokerLoginFlowAlias"
                if binding == "other-first"
                else "postBrokerLoginFlowAlias": FLOW_ALIAS,
            }
        ]
    with pytest.raises(MigrationConflict, match="serves"):
        reconcile(admin, definition, enabled=True, apply=True)
    assert writes(admin) == []


def test_complete_shared_flow_can_be_adopted_without_repair(
    admin: Mock, definition: FlowDefinition
) -> None:
    admin.flows.append(definition.model_dump(exclude={"authenticationExecutions"}))
    admin.executions.extend(
        {"id": str(i), "providerId": provider, "requirement": "ALTERNATIVE"}
        for i, provider in enumerate(PROVIDERS)
    )
    admin.get_idps.return_value = [
        {"alias": "unrelated", "firstBrokerLoginFlowAlias": FLOW_ALIAS}
    ]
    reconcile(admin, definition, enabled=True, apply=True)
    assert writes(admin) == ["update_idp"]


def test_unchanged_flow_is_validated_once(
    admin: Mock, definition: FlowDefinition
) -> None:
    reconcile(admin, definition, enabled=True, apply=True)
    admin.reset_mock()
    reconcile(admin, definition, enabled=True, apply=True)
    admin.get_authentication_flow_executions.assert_called_once_with(FLOW_ALIAS)
    assert admin.get_authentication_flow_execution.call_count == len(PROVIDERS)
    assert writes(admin) == []


@pytest.fixture
def provider_settings() -> procore_linking.ProcoreProviderSettings:
    return procore_linking.ProcoreProviderSettings(
        clientId="test-client", trustEmail=True
    )


def test_creates_the_provider_before_binding_without_touching_users(
    admin: Mock,
    definition: FlowDefinition,
    provider_settings: procore_linking.ProcoreProviderSettings,
) -> None:
    admin.provider.clear()

    def get_provider(alias: str) -> dict[str, object]:
        assert alias == "procore"
        if not admin.provider:
            raise KeycloakGetError(response_code=404)
        return copy.deepcopy(admin.provider)

    admin.get_idp.side_effect = get_provider
    admin.create_idp.side_effect = lambda payload: admin.provider.update(
        copy.deepcopy(payload)
    )
    reconcile(
        admin,
        definition,
        enabled=True,
        apply=True,
        settings=provider_settings,
        client_secret="test",
    )
    assert admin.provider["providerId"] == "oauth2"
    assert admin.provider["firstBrokerLoginFlowAlias"] == FLOW_ALIAS
    assert admin.provider["config"]["userIDClaim"] == "id"
    assert admin.provider["config"]["emailClaim"] == "login"
    assert admin.provider["config"]["clientSecret"] == "test"
    assert set(writes(admin)) <= {
        "create_authentication_flow",
        "create_authentication_flow_execution",
        "update_authentication_flow_executions",
        "create_idp",
    }


def managed_provider(
    admin: Mock, settings: procore_linking.ProcoreProviderSettings
) -> None:
    admin.provider.clear()
    admin.provider.update(
        procore_linking.provider_configuration(None, settings, "test")
    )


def test_provider_configuration_preserves_custom_binding_and_extra_settings(
    admin: Mock,
    definition: FlowDefinition,
    provider_settings: procore_linking.ProcoreProviderSettings,
) -> None:
    managed_provider(admin, provider_settings)
    admin.provider["firstBrokerLoginFlowAlias"] = "manual-first-login"
    admin.provider["postBrokerLoginFlowAlias"] = "manual-post-login"
    admin.provider["config"].update({"syncMode": "FORCE", "custom": "preserved"})
    expected = copy.deepcopy(admin.provider)
    expected["config"]["clientSecret"] = "rotated-test"
    reconcile(
        admin,
        definition,
        enabled=None,
        apply=True,
        settings=provider_settings,
        client_secret="rotated-test",
    )
    assert admin.provider == expected
    assert writes(admin) == ["update_idp"]
    admin.get_authentication_flows.assert_not_called()


@pytest.mark.parametrize(
    "change", ["clientId", "environment", "userIDClaim", "providerId"]
)
def test_refuses_to_switch_an_existing_identity_source(
    admin: Mock,
    definition: FlowDefinition,
    provider_settings: procore_linking.ProcoreProviderSettings,
    change: str,
) -> None:
    managed_provider(admin, provider_settings)
    if change == "clientId":
        provider_settings = provider_settings.model_copy(
            update={"clientId": "other-client"}
        )
    elif change == "environment":
        provider_settings = provider_settings.model_copy(
            update={"environment": "sandbox"}
        )
    elif change == "userIDClaim":
        admin.provider["config"]["userIDClaim"] = "other-subject"
    else:
        admin.provider["providerId"] = "oidc"
    with pytest.raises(MigrationConflict, match="identity source|incompatible type"):
        reconcile(
            admin,
            definition,
            enabled=True,
            apply=True,
            settings=provider_settings,
            client_secret="test",
        )
    assert writes(admin) == []


def test_provider_dry_run_and_unchanged_configuration_do_not_write(
    admin: Mock,
    definition: FlowDefinition,
    provider_settings: procore_linking.ProcoreProviderSettings,
) -> None:
    managed_provider(admin, provider_settings)
    reconcile(
        admin,
        definition,
        enabled=True,
        settings=provider_settings,
        client_secret="test",
    )
    assert writes(admin) == []
    reconcile(
        admin,
        definition,
        enabled=None,
        apply=True,
        settings=provider_settings,
        client_secret="test",
    )
    assert writes(admin) == []


@pytest.mark.parametrize("enabled", [None, True])
def test_refuses_to_remove_email_trust_from_an_active_linking_policy(
    admin: Mock,
    definition: FlowDefinition,
    provider_settings: procore_linking.ProcoreProviderSettings,
    enabled: bool | None,
) -> None:
    managed_provider(admin, provider_settings)
    admin.provider["firstBrokerLoginFlowAlias"] = FLOW_ALIAS
    settings = provider_settings.model_copy(update={"trustEmail": False})
    with pytest.raises(MigrationConflict, match="removing trust"):
        reconcile(
            admin,
            definition,
            enabled=enabled,
            apply=True,
            settings=settings,
            client_secret="test",
        )
    assert writes(admin) == []


def test_provider_settings_cannot_enable_linking_without_explicit_trust(
    admin: Mock,
    definition: FlowDefinition,
    provider_settings: procore_linking.ProcoreProviderSettings,
) -> None:
    managed_provider(admin, provider_settings)
    settings = provider_settings.model_copy(update={"trustEmail": False})
    with pytest.raises(MigrationConflict, match="trust its email"):
        reconcile(
            admin,
            definition,
            enabled=True,
            apply=True,
            settings=settings,
            client_secret="test",
        )
    assert writes(admin) == []
