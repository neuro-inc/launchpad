"""Reconcile only the dedicated Procore account-linking flow and binding."""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError, KeycloakGetError
from pydantic import BaseModel, ValidationError


FLOW_ALIAS = "procore-auto-link"
PROVIDERS = ("idp-create-user-if-unique", "idp-auto-link")


class MigrationConflict(RuntimeError):
    """Reject changes to configuration outside the migration's ownership."""


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


def set_procore_binding(
    admin: KeycloakAdmin, provider: dict[str, object], *, enabled: bool
) -> None:
    binding = provider.get("firstBrokerLoginFlowAlias") or ""
    target = FLOW_ALIAS if enabled else ""
    if binding == target:
        return
    if admin.get_idp("procore") != provider:
        raise MigrationConflict(
            "The Procore provider changed during migration; retry after review."
        )
    expected_binding = FLOW_ALIAS
    if not enabled:
        realm_name = admin.connection.realm_name
        if not realm_name:
            raise MigrationConflict("The migration realm is missing.")
        expected_binding = admin.get_realm(realm_name)["firstBrokerLoginFlow"]
    admin.update_idp("procore", {**provider, "firstBrokerLoginFlowAlias": target})
    updated = admin.get_idp("procore")
    updated_binding = updated.get("firstBrokerLoginFlowAlias") or ""
    expected = {
        key: value
        for key, value in provider.items()
        if key != "firstBrokerLoginFlowAlias"
    }
    updated_configuration = {
        key: value
        for key, value in updated.items()
        if key != "firstBrokerLoginFlowAlias"
    }
    binding_matches = updated_binding == expected_binding or (
        not enabled and not updated_binding
    )
    if updated_configuration != expected or not binding_matches:
        raise MigrationConflict("The updated Procore provider could not be verified.")


def reconcile(
    admin: KeycloakAdmin,
    definition: FlowDefinition,
    *,
    enabled: bool,
    apply: bool = False,
) -> None:
    if (
        tuple(step.authenticator for step in definition.authenticationExecutions)
        != PROVIDERS
    ):
        raise MigrationConflict("The migration definition has unexpected executions.")
    try:
        provider = admin.get_idp("procore")
    except KeycloakGetError as error:
        if error.response_code == 404:
            if not enabled:
                return
            raise MigrationConflict(
                "Configure the Procore provider before enabling linking."
            ) from None
        raise
    binding = provider.get("firstBrokerLoginFlowAlias") or ""
    if binding not in ("", "first broker login", FLOW_ALIAS):
        raise MigrationConflict(
            "Procore uses a custom first-login flow; review it manually."
        )
    if not enabled and binding != FLOW_ALIAS:
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

    set_procore_binding(admin, provider, enabled=enabled)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--realm", default="launchpad")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--flow-file", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enable", action="store_true")
    mode.add_argument("--disable", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
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
        reconcile(admin, definition, enabled=args.enable, apply=args.apply)
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
        "Procore linking migration completed."
        if args.apply
        else "Procore linking preflight passed; no changes were applied."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
