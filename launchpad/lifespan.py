import asyncio
import logging
import typing as t
from contextlib import asynccontextmanager, AsyncExitStack

import aiohttp
from launchpad.app import Launchpad
from launchpad.apps.lifespan import init_internal_apps
from launchpad.apps.service import AppService
from launchpad.apps.template_storage import seed_user_facing_templates
from launchpad.auth.oauth import Oauth
from launchpad.db.lifespan import create_db
from launchpad.ext.apps_api import AppsApiClient

logger = logging.getLogger(__name__)


async def periodic_output_processing_task(app: Launchpad) -> None:
    """Periodically process the output buffer to update app outputs."""
    while True:
        try:
            await app.app_service.process_output_buffer()
        except Exception as e:
            logger.error(f"Error in periodic output processing task: {e}")
        await asyncio.sleep(30)  # 30 seconds


@asynccontextmanager
async def create_aiohttp_session(app: Launchpad) -> t.AsyncIterator[None]:
    app.http = aiohttp.ClientSession()
    try:
        yield
    finally:
        await app.http.close()


@asynccontextmanager
async def lifespan(app: Launchpad) -> t.AsyncIterator[None]:
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(create_db(app))
        await stack.enter_async_context(create_aiohttp_session(app))
        app.apps_api_client = AppsApiClient(
            http=app.http,
            base_url=app.config.apolo.apps_api_url,
            token=app.config.apolo.token,
            cluster=app.config.apolo.cluster,
            org_name=app.config.apolo.org_name,
            project_name=app.config.apolo.project_name,
        )
        app.app_service = AppService(app=app)
        app.oauth = Oauth(
            http=app.http,
            keycloak_config=app.config.keycloak,
            cookie_domain=app.config.apolo.base_domain,
            launchpad_domain=app.config.apolo.self_domain,
        )

        # Seed user-facing templates (like OpenWebUI) on startup
        async with app.db() as db:
            async with db.begin():
                await seed_user_facing_templates(db)

        launchpad_init_task = asyncio.create_task(init_internal_apps(app))  # noqa: F841

        # Start periodic output processing task
        output_processing_task = asyncio.create_task(
            periodic_output_processing_task(app)
        )

        try:
            yield
        finally:
            # Cancel the periodic task on shutdown
            output_processing_task.cancel()
            try:
                await output_processing_task
            except asyncio.CancelledError:
                pass
