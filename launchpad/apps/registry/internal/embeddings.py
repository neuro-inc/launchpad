from typing import Any

from launchpad.apps.registry.base import App
from launchpad.apps.registry.internal.context import InternalAppContext

APP_NAME_EMBEDDINGS = "embeddings"


class EmbeddingsApp(App[InternalAppContext]):
    name = APP_NAME_EMBEDDINGS
    template_name = "text-embeddings-inference"
    template_version = "v25.7.0"
    is_internal = True
    is_shared = True
    verbose_name = "Embeddings"
    description_short = "Embeddings"
    description_long = "Embeddings"
    logo = ""
    documentation_urls = []
    external_urls = []
    tags = []

    async def _generate_inputs(self) -> dict[str, Any]:
        return {
            "ingress_http": None,
            "model": {"hf_token": {"key": "HF_TOKEN"}, "model_hf_name": "BAAI/bge-m3"},
            "displayName": APP_NAME_EMBEDDINGS,
            "preset": {"name": self._context.preset},
            "server_extra_args": [],
            "extra_env_vars": [],
        }
