from launchpad.apps.registry.internal.embeddings import (
    gen_embeddings_definition,
)
from launchpad.apps.registry.internal.llm_inference import (
    gen_llm_inference_definition,
)
from launchpad.apps.registry.internal.postgres import (
    gen_postgres_definition,
)
from launchpad.apps.registry.model import App
from launchpad.config import AppsConfig


def construct_internal_apps(apps_config: AppsConfig) -> list[App]:
    llm_inference_app = gen_llm_inference_definition(
        preset=apps_config.llm_inference_preset
    )
    embeddings_app = gen_embeddings_definition(preset=apps_config.embeddings_preset)
    postgres_app = gen_postgres_definition(preset=apps_config.postgres_preset)
    return [
        llm_inference_app,
        embeddings_app,
        postgres_app,
    ]
