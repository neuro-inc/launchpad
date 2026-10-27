"""Configure the Procore identity provider and its account-linking flow."""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError, KeycloakGetError
from pydantic import BaseModel, TypeAdapter, ValidationError


FLOW_ALIAS = "procore-auto-link"
PROVIDERS = ("idp-create-user-if-unique", "idp-auto-link")


class MigrationConflict(RuntimeError):
    """Reject changes to configuration outside the migration's ownership."""


class ProcoreProviderSettings(BaseModel):
    clientId: str
    environment: Literal["production", "sandbox"] = "production"
    enabled: bool = True
    trustEmail: bool = False


def provider_configuration(
    current: dict[str, object] | None,
    settings: ProcoreProviderSettings,
    client_secret: str,
) -> dict[str, object]:
    if not settings.clientId.strip() or not client_secret:
        raise MigrationConflict(
            "The Procore client ID and client secret must not be empty."
        )
    login_host, api_host = (
        ("login.procore.com", "api.procore.com")
        if settings.environment == "production"
        else ("login-sandbox.procore.com", "sandbox.procore.com")
    )
    identity = {
        "clientId": settings.clientId,
        "authorizationUrl": f"https://{login_host}/oauth/authorize",
        "tokenUrl": f"https://{login_host}/oauth/token",
        "userInfoUrl": f"https://{api_host}/rest/v1.0/me",
        "userIDClaim": "id",
        "userNameClaim": "login",
        "emailClaim": "login",
    }
    configuration = TypeAdapter(dict[str, str]).validate_python(
        (current or {}).get("config", {})
    )
    if current:
        if current.get("providerId") != "oauth2":
            raise MigrationConflict(
                "The existing Procore provider has an incompatible type."
            )
        for key, expected in identity.items():
            observed = configuration.get(key, "")
            if key.endswith("Url"):
                observed, expected = observed.rstrip("/"), expected.rstrip("/")
            if observed != expected:
                raise MigrationConflict(
                    "The existing Procore identity source differs; review it manually."
                )
    else:
        configuration = {
            "clientAuthMethod": "client_secret_post",
            "syncMode": "LEGACY",
            "fullNameClaim": "name",
        }
    return {
        **(
            current
            or {
                "alias": "procore",
                "providerId": "oauth2",
                "displayName": "Procore",
                "storeToken": False,
            }
        ),
        "enabled": settings.enabled,
        "trustEmail": settings.trustEmail,
        "config": {**configuration, **identity, "clientSecret": client_secret},
    }


def get_procore_provider(admin: KeycloakAdmin) -> dict[str, object] | None:
    try:
        return admin.get_idp("procore")
    except KeycloakGetError as error:
        if error.response_code == 404:
            return None
        raise


class ExecutionDefinition(BaseModel):
    authenticator: str
    authenticatorFlow: Literal[False]
    requirement: Literal["ALTERNATIVE"]
    priority: int


class FlowDefinition(BaseModel):
    alias: Literal["procore-auto-link"]
    description: str
    providerId: Literal["basic-flow"]
    topLevel: Literal[True]
    builtIn: Literal[False]
    authenticationExecutions: list[ExecutionDefinition]


class FlowState(BaseModel):
    alias: str
    description: str = ""
    providerId: str
    topLevel: bool
    builtIn: bool


class ExecutionState(BaseModel):
    id: str
    providerId: str
    requirement: str
    authenticationFlow: bool = False
    level: int = 0


class ExecutionDetails(BaseModel):
    authenticatorConfig: str | None = None


class ProviderBindings(BaseModel):
    alias: str
    firstBrokerLoginFlowAlias: str | None = None
    postBrokerLoginFlowAlias: str | None = None


def flow_executions(admin: KeycloakAdmin) -> list[ExecutionState]:
    return [
        ExecutionState.model_validate(value)
        for value in admin.get_authentication_flow_executions(FLOW_ALIAS)
    ]


def validate_executions(admin: KeycloakAdmin, executions: list[ExecutionState]) -> None:
    providers = tuple(execution.providerId for execution in executions)
    if providers != PROVIDERS[: len(providers)]:
        raise MigrationConflict("The existing Procore flow has unexpected executions.")
    for execution in executions:
        details = ExecutionDetails.model_validate(
            admin.get_authentication_flow_execution(execution.id)
        )
        if (
            execution.authenticationFlow
            or execution.level != 0
            or execution.requirement not in ("DISABLED", "ALTERNATIVE")
            or details.authenticatorConfig
        ):
            raise MigrationConflict(
                "The existing Procore flow contains custom settings."
            )


def validate_exclusive_flow(admin: KeycloakAdmin) -> None:
    realm_name = admin.connection.realm_name
    if not realm_name:
        raise MigrationConflict("The migration realm is missing.")
    realm = admin.get_realm(realm_name)
    if any(
        key.endswith("Flow") and value == FLOW_ALIAS for key, value in realm.items()
    ):
        raise MigrationConflict(
            "The Procore flow serves a realm binding; review it manually."
        )
    for value in admin.get_idps():
        provider = ProviderBindings.model_validate(value)
        shared_first_login = (
            provider.alias != "procore"
            and provider.firstBrokerLoginFlowAlias == FLOW_ALIAS
        )
        if shared_first_login or provider.postBrokerLoginFlowAlias == FLOW_ALIAS:
            raise MigrationConflict(
                "The Procore flow serves another login binding; review it manually."
            )


def write_procore_provider(
    admin: KeycloakAdmin,
    current: dict[str, object] | None,
    desired: dict[str, object],
) -> None:
    if current == desired:
        return
    if get_procore_provider(admin) != current:
        raise MigrationConflict(
            "The Procore provider changed during migration; retry after review."
        )
    expected_binding = desired.get("firstBrokerLoginFlowAlias") or ""
    if not expected_binding:
        realm_name = admin.connection.realm_name
        if not realm_name:
            raise MigrationConflict("The migration realm is missing.")
        expected_binding = admin.get_realm(realm_name)["firstBrokerLoginFlow"]
    if current is None:
        admin.create_idp(desired)
    else:
        admin.update_idp("procore", desired)
    updated = admin.get_idp("procore")
    updated_binding = updated.get("firstBrokerLoginFlowAlias") or ""
    binding_matches = updated_binding == expected_binding or (
        not desired.get("firstBrokerLoginFlowAlias") and not updated_binding
    )
    desired_config = TypeAdapter(dict[str, str]).validate_python(
        desired.get("config", {})
    )
    updated_config = TypeAdapter(dict[str, str]).validate_python(
        updated.get("config", {})
    )
    expected_secret = desired_config.pop("clientSecret", None)
    observed_secret = updated_config.pop("clientSecret", None)
    secret_matches = expected_secret is None or observed_secret in (
        expected_secret,
        "**********",
    )
    expected = {
        key: value
        for key, value in desired.items()
        if key not in ("firstBrokerLoginFlowAlias", "config")
    }
    observed = {
        key: value
        for key, value in updated.items()
        if key not in ("firstBrokerLoginFlowAlias", "config")
    }
    fields_match = (
        observed == expected
        if current is not None
        else all(observed.get(key) == value for key, value in expected.items())
    )
    if not (
        fields_match
        and desired_config == updated_config
        and binding_matches
        and secret_matches
    ):
        raise MigrationConflict("The updated Procore provider could not be verified.")


def reconcile(
    admin: KeycloakAdmin,
    definition: FlowDefinition,
    *,
    enabled: bool | None,
    apply: bool = False,
    settings: ProcoreProviderSettings | None = None,
    client_secret: str | None = None,
) -> None:
    if (
        tuple(step.authenticator for step in definition.authenticationExecutions)
        != PROVIDERS
    ):
        raise MigrationConflict("The migration definition has unexpected executions.")
    current_provider = get_procore_provider(admin)
    if settings is not None:
        if client_secret is None:
            raise MigrationConflict("The Procore client secret file is required.")
        provider = provider_configuration(current_provider, settings, client_secret)
    elif current_provider is not None:
        provider = current_provider.copy()
    else:
        if not enabled:
            return
        raise MigrationConflict(
            "Configure the Procore provider before enabling linking."
        )
    binding = provider.get("firstBrokerLoginFlowAlias") or ""
    if enabled is not None and binding not in ("", "first broker login", FLOW_ALIAS):
        raise MigrationConflict(
            "Procore uses a custom first-login flow; review it manually."
        )
    if (
        binding == FLOW_ALIAS
        and provider.get("enabled") is True
        and provider.get("trustEmail") is not True
        and enabled is not False
    ):
        raise MigrationConflict(
            "Disable automatic linking before removing trust in Procore email claims."
        )
    if not enabled and binding != FLOW_ALIAS:
        if apply:
            write_procore_provider(admin, current_provider, provider)
        return
    if enabled and (
        provider.get("trustEmail") is not True or provider.get("enabled") is not True
    ):
        raise MigrationConflict(
            "Procore must be enabled and explicitly trust its email claims."
        )

    flows = [
        FlowState.model_validate(value) for value in admin.get_authentication_flows()
    ]
    existing = next((flow for flow in flows if flow.alias == FLOW_ALIAS), None)
    executions: list[ExecutionState] = []
    if existing:
        if (
            existing.builtIn
            or not existing.topLevel
            or existing.providerId != "basic-flow"
        ):
            raise MigrationConflict(
                "The existing Procore flow has an incompatible type."
            )
        executions = flow_executions(admin)
        validate_executions(admin, executions)
        if (
            len(executions) != len(PROVIDERS)
            or any(step.requirement != "ALTERNATIVE" for step in executions)
        ) and existing.description != definition.description:
            raise MigrationConflict(
                "An incomplete custom Procore flow cannot be adopted."
            )
    elif not enabled:
        raise MigrationConflict(
            "The bound Procore flow is missing; review it manually."
        )

    needs_repair = len(executions) != len(PROVIDERS) or any(
        step.requirement != "ALTERNATIVE" for step in executions
    )
    if enabled is None and needs_repair:
        raise MigrationConflict(
            "Select automatic linking explicitly before repairing its flow."
        )
    if enabled and needs_repair:
        validate_exclusive_flow(admin)

    if not apply:
        return
    if enabled and needs_repair:
        if not existing:
            admin.create_authentication_flow(
                definition.model_dump(exclude={"authenticationExecutions"})
            )
        for step in definition.authenticationExecutions[len(executions) :]:
            admin.create_authentication_flow_execution(
                payload={"provider": step.authenticator}, flow_alias=FLOW_ALIAS
            )
        executions = flow_executions(admin)
        validate_executions(admin, executions)
        if len(executions) != len(PROVIDERS):
            raise MigrationConflict("The Procore flow is incomplete.")
        for execution in executions:
            if execution.requirement != "ALTERNATIVE":
                admin.update_authentication_flow_executions(
                    payload={"id": execution.id, "requirement": "ALTERNATIVE"},
                    flow_alias=FLOW_ALIAS,
                )
        verified = flow_executions(admin)
        validate_executions(admin, verified)
        if len(verified) != len(PROVIDERS) or any(
            step.requirement != "ALTERNATIVE" for step in verified
        ):
            raise MigrationConflict(
                "The Procore flow requirements could not be verified."
            )

    if enabled is not None:
        provider["firstBrokerLoginFlowAlias"] = FLOW_ALIAS if enabled else ""
    write_procore_provider(admin, current_provider, provider)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--realm", default="launchpad")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--flow-file", required=True, type=Path)
    parser.add_argument("--provider-file", type=Path)
    parser.add_argument("--client-secret-file", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enable", action="store_true")
    mode.add_argument("--disable", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if bool(args.provider_file) != bool(args.client_secret_file):
        parser.error("Supply both provider and client-secret files.")
    if not (args.enable or args.disable or args.provider_file):
        parser.error("Select a linking mode or supply provider configuration.")
    server = urlsplit(args.server)
    if (
        server.scheme not in ("http", "https")
        or not server.hostname
        or server.username
        or server.password
        or server.query
        or server.fragment
    ):
        parser.error(
            "The server must be an HTTP or HTTPS origin without credentials or query parameters."
        )
    try:
        definition = FlowDefinition.model_validate_json(args.flow_file.read_text())
        settings = (
            ProcoreProviderSettings.model_validate_json(args.provider_file.read_text())
            if args.provider_file
            else None
        )
        client_secret = (
            args.client_secret_file.read_text().rstrip("\r\n")
            if args.client_secret_file
            else None
        )
        admin = KeycloakAdmin(
            server_url=args.server.rstrip("/") + "/",
            realm_name=args.realm,
            user_realm_name="master",
            username=args.username,
            password=Path(args.password_file).read_text().rstrip("\r\n"),
            verify=True,
            timeout=20,
            max_retries=0,
        )
        enabled = args.enable if args.enable or args.disable else None
        reconcile(
            admin,
            definition,
            enabled=enabled,
            apply=args.apply,
            settings=settings,
            client_secret=client_secret,
        )
    except MigrationConflict as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeycloakError as error:
        print(f"Keycloak request failed (HTTP {error.response_code}).", file=sys.stderr)
        return 1
    except (OSError, ValidationError, json.JSONDecodeError):
        print("The migration inputs could not be read or validated.", file=sys.stderr)
        return 1
    print(
        "Procore configuration completed."
        if args.apply
        else "Procore linking preflight passed; no changes were applied."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
