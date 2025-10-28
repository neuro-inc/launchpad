import typing as t

import apolo_sdk
from apolo_app_types.clients.kube import get_service_host_port
from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.common import INSTANCE_LABEL
from apolo_app_types.outputs.utils.ingress import get_ingress_host_port
from apolo_app_types.protocols.common.middleware import AuthIngressMiddleware
from apolo_app_types.protocols.common.networking import HttpApi, ServiceAPI, WebApp
from apolo_app_types.protocols.common.secrets_ import ApoloSecret

from .types import (
    KeycloakConfig,
    LaunchpadAdminApi,
    LaunchpadAppOutputs,
    LaunchpadDefaultAdminUser,
)


def get_launchpad_name(apolo_app_id: str) -> str:
    """
    Construct launchpad name using helm chart logic.
    Mirrors the template: {{ printf "launchpad-%s" .Values.apolo_app_id | trunc 63 | trimSuffix "-" }}
    """
    return f"launchpad-{apolo_app_id}"[:63].rstrip("-")


async def create_apolo_secret(
    app_instance_id: str, key: str, value: str
) -> ApoloSecret:
    secret_key = f"{key}-{app_instance_id}"
    try:
        async with apolo_sdk.get() as client:
            bytes_value = value.encode("utf-8")
            await client.secrets.add(key=secret_key, value=bytes_value)
    except Exception as e:
        print("Failed to create Apolo Secret")
        raise (e)
    return ApoloSecret(key=secret_key)


async def get_launchpad_outputs(
    helm_values: dict[str, t.Any],
    app_instance_id: str,
) -> dict[str, t.Any]:
    labels = {
        "application": "launchpad",
        INSTANCE_LABEL: app_instance_id,
    }

    launchpad_labels = {
        **labels,
        "service": "client",
    }
    internal_host, internal_port = await get_service_host_port(
        match_labels=launchpad_labels
    )
    internal_web_app_url = None
    if internal_host:
        internal_web_app_url = WebApp(
            host=internal_host,
            port=int(internal_port),
            base_path="/",
            protocol="http",
        )

    host_port = await get_ingress_host_port(match_labels=launchpad_labels)
    external_web_app_url = None
    if host_port:
        host, port = host_port
        external_web_app_url = WebApp(
            host=host,
            port=int(port),
            base_path="/",
            protocol="https",
        )

    # -------------- API ----------------
    launchpad_api_labels = {
        **labels,
        "service": "launchpad",
    }
    internal_host, internal_port = await get_service_host_port(
        match_labels=launchpad_api_labels
    )
    internal_api_url = None
    if internal_host:
        internal_api_url = HttpApi(
            host=internal_host,
            port=int(internal_port),
            base_path="/",
            protocol="http",
        )

    host_port = await get_ingress_host_port(match_labels=launchpad_api_labels)
    external_api_url = None
    if host_port:
        host, port = host_port
        external_api_url = HttpApi(
            host=host,
            port=int(port),
            base_path="/",
            protocol="https",
        )

    # -------------- KEYCLOAK ----------------
    # keycloak urls
    keycloak_labels = {
        **labels,
        "service": "keycloak",
    }

    host_port = await get_ingress_host_port(match_labels=keycloak_labels)
    keycloak_external_web_app_url = None
    if host_port:
        host, port = host_port
        keycloak_external_web_app_url = HttpApi(
            host=host,
            port=int(port),
            base_path="/",
            protocol="https",
        )

    internal_host, internal_port = await get_service_host_port(
        match_labels=keycloak_labels
    )
    keycloak_internal_web_app_url = None
    if internal_host:
        keycloak_internal_web_app_url = HttpApi(
            host=internal_host,
            port=int(internal_port),
            base_path="/",
            protocol="http",
        )

    keycloak_password = helm_values["keycloak"]["auth"]["adminPassword"]

    # -------------- MIDDLEWARE ----------------
    # Construct middleware name using helm chart logic: launchpad-{apolo_app_id}-auth-middleware
    launchpad_name = get_launchpad_name(helm_values.get("apolo_app_id", ""))
    middleware_name = f"platform-{launchpad_name}-auth-middleware"
    print(f"App instance ID: {app_instance_id}")
    print(f"Apolo App ID: {helm_values.get('apolo_app_id', '')}")
    print(f"Launchpad name: {launchpad_name}")
    print(f"Full middleware name: {middleware_name}")

    # -------------- FINAL OUTPUT ----------------
    outputs = LaunchpadAppOutputs(
        app_url=ServiceAPI[WebApp](
            internal_url=internal_web_app_url,
            external_url=external_web_app_url,
        ),
        keycloak_config=KeycloakConfig(
            web_app_url=ServiceAPI[HttpApi](
                internal_url=keycloak_internal_web_app_url,
                external_url=keycloak_external_web_app_url,
            ),
            auth_admin_password=await create_apolo_secret(
                app_instance_id=app_instance_id, key="keycloak", value=keycloak_password
            ),
        ),
        installed_apps=None,
        auth_middleware=AuthIngressMiddleware(name=middleware_name),
        admin_user=LaunchpadDefaultAdminUser(
            username=helm_values["LAUNCHPAD_ADMIN_USER"],
            email=helm_values["LAUNCHPAD_ADMIN_EMAIL"],
            password=await create_apolo_secret(
                app_instance_id=app_instance_id,
                key="launchpad-admin",
                value=helm_values["LAUNCHPAD_ADMIN_PASSWORD"],
            ),
        ),
        admin_api=LaunchpadAdminApi(
            api_url=ServiceAPI[HttpApi](
                internal_url=internal_api_url,
                external_url=external_api_url,
            )
        ),
    )
    return outputs.model_dump()


class LaunchpadOutputProcessor(BaseAppOutputsProcessor[LaunchpadAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> LaunchpadAppOutputs:
        return LaunchpadAppOutputs.model_validate(
            await get_launchpad_outputs(helm_values, app_instance_id)
        )
