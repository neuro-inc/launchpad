import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from launchpad.app import Launchpad
from launchpad.apps.registry.internal.context import InternalAppContext
from launchpad.apps.registry.base import App
from launchpad.apps.registry.internal.embeddings import EmbeddingsApp
from launchpad.apps.registry.internal.llm_inference import LlmInferenceApp
from launchpad.apps.registry.internal.postgres import PostgresApp
from launchpad.apps.storage import select_app, insert_app, delete_app
from launchpad.apps.service import is_healthy
from launchpad.ext.apps_api import AppsApiClient

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
                sessionmaker=app.db,
                apps_api_client=app.apps_api_client,
                internal_app=internal_app,
            )
        except Exception:
            logger.exception(f"unable to initialize an internal app: {internal_app}")
            continue


async def init_internal_app(
    sessionmaker: async_sessionmaker[AsyncSession],
    apps_api_client: AppsApiClient,
    internal_app: App[InternalAppContext],
) -> None:
    """
    Initializes a single internal app
    """
    async with sessionmaker() as db:
        existing_app = await select_app(db, name=internal_app.name, is_internal=True)

    if existing_app is not None:
        if await is_healthy(apps_api_client, existing_app):
            # app is healthy, so nothing to do more here
            return

        # an app is not healthy, but exists in a DB. let's remove it
        async with sessionmaker() as db:
            async with db.begin():
                await delete_app(db, existing_app.app_id)

    installation_response = await apps_api_client.install_app(
        payload=await internal_app.to_apps_api_payload()
    )

    # persist record in a DB
    async with sessionmaker() as db:
        async with db.begin():
            await insert_app(
                db=db,
                app_id=installation_response["id"],
                app_name=installation_response["name"],
                launchpad_app_name=internal_app.name,
                is_internal=internal_app.is_internal,
                is_shared=internal_app.is_shared,
                user_id=None,
                url=None,
            )
