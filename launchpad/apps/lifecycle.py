import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from launchpad.app import Launchpad
from launchpad.apps.models import InstalledApp
from launchpad.apps.registry.internal import construct_internal_apps
from launchpad.apps.registry.model import App
from launchpad.apps.storage import select_app, insert_app, delete_app
from launchpad.ext.apps_api import NotFound, AppsApiClient

logger = logging.getLogger(__name__)


HEALTHY_STATUSES = {"queued", "progressing", "healthy"}


# todo: make this a periodic task to sync the statuses of the internal apps with the apps api ?
async def init_internal_apps(app: Launchpad) -> None:
    internal_apps = construct_internal_apps(apps_config=app.config.apps)

    for internal_app in internal_apps:
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
    internal_app: App,
) -> None:
    """
    Initializes a single internal app
    """
    async with sessionmaker() as db:
        existing_app = await select_app(db, name=internal_app.name, is_internal=True)

    if existing_app is not None:
        is_healthy = await _is_healthy(apps_api_client, existing_app)
        if is_healthy:
            # app is healthy, so nothing to do more here
            return

        # an app is not healthy, but exists in a DB. let's remove it
        async with sessionmaker() as db:
            async with db.begin():
                await delete_app(db, existing_app.app_id)

    installation_response = await apps_api_client.install_app(
        payload=internal_app.to_apps_api_payload()
    )

    # persist record in a DB
    async with sessionmaker() as db:
        async with db.begin():
            await insert_app(
                db=db,
                app_id=installation_response["id"],
                app_name=installation_response["name"],
                launchpad_name=internal_app.name,
                is_internal=internal_app.is_internal,
                is_shared=internal_app.is_shared,
                user_id=None,
                url=None,
            )


async def _is_healthy(
    app_api_client: AppsApiClient,
    existing_app: InstalledApp,
) -> bool:
    try:
        apps_api_response = await app_api_client.get_by_id(app_id=existing_app.app_id)
    except NotFound:
        return False
    return apps_api_response["state"] in HEALTHY_STATUSES
