from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.clients.kube import get_service_host_port, get_middlewares
from apolo_app_types.outputs.common import INSTANCE_LABEL
from apolo_app_types.outputs.utils.ingress import get_ingress_host_port
from apolo_app_types.protocols.common.networking import HttpApi, ServiceAPI, WebApp
from apolo_app_types.protocols.common.middleware import AuthIngressMiddleware
from .types import (
    KeycloakConfig,
    LaunchpadAppOutputs,
)
import typing as t


def get_launchpad_name(apolo_app_id: str) -> str:
    """
    Construct launchpad name using helm chart logic.
    Mirrors the template: {{ printf "launchpad-%s" .Values.apolo_app_id | trunc 63 | trimSuffix "-" }}
    """
    return f"launchpad-{apolo_app_id}"[:63].rstrip("-")


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

    # Construct middleware name using helm chart logic: launchpad-{apolo_app_id}-auth-middleware
    launchpad_name = get_launchpad_name(app_instance_id)
    middleware_name = f"{launchpad_name}-auth-middleware"

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
            auth_admin_password=keycloak_password,
            auth_middleware=AuthIngressMiddleware(
                name=f"platform-{middleware_name}"
            )
        ),
        installed_apps=None,
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
