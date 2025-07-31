import logging

from launchpad.app import Launchpad
from launchpad.apps.registry.base import App
from launchpad.apps.registry.internal.context import InternalAppContext
from launchpad.apps.registry.internal.embeddings import EmbeddingsApp
from launchpad.apps.registry.internal.llm_inference import LlmInferenceApp
from launchpad.apps.registry.internal.postgres import PostgresApp
from launchpad.apps.service import AppService, AppNotInstalledError, AppUnhealthyError

logger = logging.getLogger(__name__)


# todo: make this a periodic task to sync the statuses of the internal apps with the apps api ?
async def init_internal_apps(app: Launchpad) -> None:
    llm_inference_context = InternalAppContext(
        preset=app.config.apps.llm_inference_preset
    )
    embeddings_context = InternalAppContext(preset=app.config.apps.embeddings_preset)
    postgres_context = InternalAppContext(preset=app.config.apps.postgres_preset)

    for internal_app in (
        LlmInferenceApp(context=llm_inference_context),
        EmbeddingsApp(context=embeddings_context),
        PostgresApp(context=postgres_context),
    ):
        try:
            await init_internal_app(
                app_service=app.app_service,
                internal_app=internal_app,
            )
        except Exception:
            logger.exception(f"unable to initialize an internal app: {internal_app}")
            continue


async def init_internal_app(
    app_service: AppService,
    internal_app: App[InternalAppContext],
) -> None:
    """
    Initializes a single internal app
    """
    try:
        await app_service.get_installed_app(
            launchpad_app_name=internal_app.name,
            with_url=False,  # internal apps doesn't expose apps URLs
        )
    except AppNotInstalledError:
        logger.info(f"internal app {internal_app} is not yet installed.")
    except AppUnhealthyError as e:
        # delete so we can try to re-install
        logger.info(f"internal app {internal_app} is unhealthy. trying to recreate")
        await app_service.delete(e.app_id)
    else:
        # an app is installed and is healthy
        logger.info(f"internal app {internal_app} is already installed and running")
        return

    logger.info(f"installing internal app {internal_app}")
    await app_service.install(internal_app)
    logger.info(f"installed an internal app {internal_app}")
