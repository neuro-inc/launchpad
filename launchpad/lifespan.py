import asyncio
import logging
import typing as t
from contextlib import asynccontextmanager, AsyncExitStack

import aiohttp
from launchpad.app import Launchpad
from launchpad.apps.lifespan import init_internal_apps
from launchpad.apps.service import AppService
from launchpad.auth.oauth import Oauth
from launchpad.db.lifespan import create_db
from launchpad.ext.apps_api import AppsApiClient

logger = logging.getLogger(__name__)


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
        launchpad_init_task = asyncio.create_task(init_internal_apps(app))  # noqa: F841
        yield
