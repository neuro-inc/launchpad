import dataclasses
from typing import Any, Self
from uuid import UUID

from starlette.requests import Request

from launchpad.apps.registry.base import App
from launchpad.apps.registry.base import BaseContext
from launchpad.apps.registry.internal.embeddings import APP_NAME_EMBEDDINGS
from launchpad.apps.registry.internal.llm_inference import APP_NAME_LLM_INFERENCE
from launchpad.apps.registry.internal.postgres import APP_NAME_POSTGRES
from launchpad.apps.service import AppNotInstalledError, AppUnhealthyError
from launchpad.errors import BadRequest

APP_NAME_OPEN_WEB_UI = "openwebui"


@dataclasses.dataclass
class OpenWebUIAppContext(BaseContext):
    llm_inference_app_id: UUID
    embeddings_app_id: UUID
    postgres_app_id: UUID

    @classmethod
    async def from_request(
        cls,
        request: Request,
    ) -> Self:
        app_service = request.app.app_service
        params: dict[str, UUID] = {}

        for required_app_name, context_property_name in (
            (APP_NAME_LLM_INFERENCE, "llm_inference_app_id"),
            (APP_NAME_EMBEDDINGS, "embeddings_app_id"),
            (APP_NAME_POSTGRES, "postgres_app_id"),
        ):
            try:
                installed_app = await app_service.get_installed_app(
                    required_app_name, with_url=False
                )
            except AppNotInstalledError:
                raise BadRequest(f"Missing required dependency: {required_app_name}")
            except AppUnhealthyError:
                raise BadRequest(f"Dependant app is not healthy: {required_app_name}")
            params[context_property_name] = installed_app.app_id

        return cls(**params)


class OpenWebUIApp(App[OpenWebUIAppContext]):
    name = APP_NAME_OPEN_WEB_UI
    template_name = "openwebui"
    template_version = "v25.7.0"
    is_internal = False
    is_shared = True
    verbose_name = "OpenWebUI"
    description_short = "OpenWebUI"
    description_long = "OpenWebUI"
    logo = ""
    documentation_urls = []
    external_urls = []
    tags = []

    async def _generate_inputs(self) -> dict[str, Any]:
        return {
            "ingress_http": {"auth": True},
            "embeddings_api": {
                "type": "app-instance-ref",
                "instance_id": str(self._context.embeddings_app_id),
                "path": "$.internal_api",
            },
            "llm_chat_api": {
                "type": "app-instance-ref",
                "instance_id": str(self._context.llm_inference_app_id),
                "path": "$.chat_internal_api",
            },
            "pgvector_user": {
                "type": "app-instance-ref",
                "instance_id": str(self._context.postgres_app_id),
                "path": "$.postgres_users.users[1]",
            },
            "displayName": APP_NAME_OPEN_WEB_UI,
            "preset": {"name": "cpu-medium"},
            "openwebui_specific": {"env": []},
        }
