import dataclasses
from typing import Any, Self
from uuid import UUID

from starlette.requests import Request

from launchpad.apps.registry.base import App
from launchpad.apps.registry.base import BaseContext
from launchpad.apps.registry.internal.embeddings import APP_NAME_EMBEDDINGS
from launchpad.apps.registry.internal.llm_inference import APP_NAME_LLM_INFERENCE
from launchpad.apps.registry.internal.postgres import APP_NAME_POSTGRES
from launchpad.auth import (
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_AUTH_REQUEST_GROUPS,
)
from launchpad.errors import BadRequest

APP_NAME_OPEN_WEB_UI = "openwebui"


@dataclasses.dataclass
class OpenWebUIAppContext(BaseContext):
    llm_inference_app_id: UUID
    embeddings_app_id: UUID
    postgres_app_id: UUID
    auth_middleware_name: str

    @classmethod
    async def from_request(
        cls,
        request: Request,
    ) -> Self:
        # todo: fix this circular import
        from launchpad.apps.service import AppNotInstalledError, AppUnhealthyError

        app_service = request.app.app_service
        params = {
            "auth_middleware_name": request.app.config.apolo.auth_middleware_name,
        }

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
    template_version = "latest"  # we can lock this later when app versioning is working

    is_internal = False
    is_shared = True
    verbose_name = "OpenWebUI"
    description_short = (
        "An extensible, self-hosted AI interface that adapts to your workflow."
    )
    description_long = (
        "Open WebUI is an extensible, feature-rich, and user-friendly "
        "self-hosted AI platform designed to operate entirely offline. "
        "It supports various LLM runners like Ollama and "
        "OpenAI-compatible APIs, with built-in inference engine for RAG, "
        "making it a powerful AI deployment solution."
    )
    logo = "https://storage.googleapis.com/development-421920-assets/app-logos/openwebui-logo.png"
    documentation_urls = [
        {
            "text": "OpenWebUI Repository",
            "url": "https://github.com/open-webui/open-webui",
        },
        {"text": "OpenWebUI Documentation", "url": "https://docs.openwebui.com/"},
    ]
    external_urls = [
        {
            "text": "OpenWebUI Repository",
            "url": "https://github.com/open-webui/open-webui",
        }
    ]
    tags = ["Text", "Chat", "RAG"]

    async def _generate_inputs(self) -> dict[str, Any]:
        return {
            "networking_config": {
                "ingress_http": {
                    "auth": {
                        "middleware": {"name": self._context.auth_middleware_name},
                        "type": "custom_auth",
                    }
                },
            },
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
            "database_config": {
                "database": {
                    "database_type": "postgres",
                    "credentials": {
                        "type": "app-instance-ref",
                        "instance_id": str(self._context.postgres_app_id),
                        "path": "$.postgres_users.users[0]",
                    },
                }
            },
            "displayName": APP_NAME_OPEN_WEB_UI,
            "preset": {"name": "cpu-medium"},
            "openwebui_specific": {
                "env": [
                    {
                        "name": "DEFAULT_USER_ROLE",
                        "value": "user",
                    },
                    {
                        "name": "ENABLE_OAUTH_SIGNUP",
                        "value": "true",
                    },
                    {
                        "name": "ENABLE_OAUTH_GROUP_MANAGEMENT",
                        "value": "true",
                    },
                    {
                        "name": "ENABLE_OAUTH_GROUP_CREATION",
                        "value": "true",
                    },
                    {
                        "name": "OAUTH_GROUPS_CLAIM",
                        "value": "groups",
                    },
                    {
                        "name": "ENABLE_OAUTH_ROLE_MANAGEMENT",
                        "value": "true",
                    },
                    {
                        "name": "OAUTH_ALLOWED_ROLES",
                        "value": "admin,user",
                    },
                    {
                        "name": "OAUTH_ADMIN_ROLES",
                        "value": "admin",
                    },
                    {
                        "name": "OAUTH_ROLES_CLAIM",
                        "value": "realm_access.roles",
                    },
                    {
                        "name": "WEBUI_AUTH_TRUSTED_EMAIL_HEADER",
                        "value": HEADER_X_AUTH_REQUEST_EMAIL,
                    },
                    {
                        "name": "WEBUI_AUTH_TRUSTED_NAME_HEADER",
                        "value": HEADER_X_AUTH_REQUEST_USERNAME,
                    },
                    {
                        "name": "WEBUI_AUTH_TRUSTED_GROUPS_HEADER",
                        "value": HEADER_X_AUTH_REQUEST_GROUPS,
                    },
                    {
                        "name": "ENABLE_SIGNUP",
                        "value": "true",
                    },
                    {"name": "GLOBAL_LOG_LEVEL", "value": "DEBUG"},
                ]
            },
        }
