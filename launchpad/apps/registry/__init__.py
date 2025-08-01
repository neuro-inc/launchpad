from launchpad.apps.registry.base import App
from launchpad.apps.registry.internal.context import InternalAppContext
from launchpad.apps.registry.internal.embeddings import (
    EmbeddingsApp,
    APP_NAME_EMBEDDINGS,
)
from launchpad.apps.registry.internal.llm_inference import (
    LlmInferenceApp,
    APP_NAME_LLM_INFERENCE,
)
from launchpad.apps.registry.internal.postgres import PostgresApp, APP_NAME_POSTGRES
from launchpad.apps.registry.shared.openwebui import (
    APP_NAME_OPEN_WEB_UI,
    OpenWebUIApp,
    OpenWebUIAppContext,
)

T_App = OpenWebUIApp | App[InternalAppContext]

APPS: dict[str, type[T_App]] = {
    APP_NAME_LLM_INFERENCE: LlmInferenceApp,
    APP_NAME_EMBEDDINGS: EmbeddingsApp,
    APP_NAME_POSTGRES: PostgresApp,
    APP_NAME_OPEN_WEB_UI: OpenWebUIApp,
}

USER_FACING_APPS = {
    APP_NAME_OPEN_WEB_UI: OpenWebUIApp,
}


APPS_CONTEXT = {
    APP_NAME_OPEN_WEB_UI: OpenWebUIAppContext,
}
