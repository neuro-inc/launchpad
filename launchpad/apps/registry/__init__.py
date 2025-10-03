from launchpad.apps.registry.base import App, GenericApp
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
from launchpad.apps.registry.handlers.service_deployment import (
    ServiceDeploymentApp,
    ServiceDeploymentContext,
)

T_App = OpenWebUIApp | App[InternalAppContext] | GenericApp

# Legacy: Maps template names to App classes
# This is now used to determine if a template has a specific handler
TEMPLATE_HANDLERS: dict[str, type[T_App]] = {
    APP_NAME_LLM_INFERENCE: LlmInferenceApp,
    APP_NAME_EMBEDDINGS: EmbeddingsApp,
    APP_NAME_POSTGRES: PostgresApp,
    APP_NAME_OPEN_WEB_UI: OpenWebUIApp,
}

# Maps handler class names to App classes
# Used for dynamic lookup from AppTemplate.handler_class
HANDLER_CLASSES: dict[str, type[T_App]] = {
    LlmInferenceApp.__name__: LlmInferenceApp,
    EmbeddingsApp.__name__: EmbeddingsApp,
    PostgresApp.__name__: PostgresApp,
    OpenWebUIApp.__name__: OpenWebUIApp,
    ServiceDeploymentApp.__name__: ServiceDeploymentApp,
}

# Maps template names to context classes (for templates that need special context)
APPS_CONTEXT = {
    OpenWebUIApp.__name__: OpenWebUIAppContext,
    ServiceDeploymentApp.__name__: ServiceDeploymentContext,
}

# Legacy compatibility
APPS = TEMPLATE_HANDLERS
USER_FACING_APPS = {
    APP_NAME_OPEN_WEB_UI: OpenWebUIApp,
}
