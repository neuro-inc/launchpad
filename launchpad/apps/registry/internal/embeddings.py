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
        return self._context.merge_with_inputs(
            inputs={
                "ingress_http": None,
                "displayName": APP_NAME_EMBEDDINGS,
                "extra_env_vars": [],
            }
        )
