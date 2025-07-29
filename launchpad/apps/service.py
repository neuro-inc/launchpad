from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from launchpad.apps.models import InstalledApp
from launchpad.apps.registry import APPS, APPS_CONTEXT, T_App
from launchpad.apps.storage import select_app
from launchpad.ext.apps_api import AppsApiClient, NotFound, AppsApiError

HEALTHY_STATUSES = {"queued", "progressing", "healthy"}


class AppServiceError(Exception): ...


class AppNotInstalledError(AppServiceError): ...


class AppUnhealthyError(AppServiceError): ...


class AppTemplateNotFound(AppServiceError): ...


class AppMissingUrlError(AppServiceError): ...


async def get_installed_app(
    db: AsyncSession,
    apps_api_client: AppsApiClient,
    launchpad_app_name: str,
    user_id: str | None = None,
) -> InstalledApp:
    select_params: dict[str, Any] = {"name": launchpad_app_name}
    if user_id is not None:
        select_params["user_id"] = user_id

    installed_app = await select_app(db, **select_params)

    if installed_app is None:
        raise AppNotInstalledError()

    if not await is_healthy(apps_api_client, installed_app):
        raise AppUnhealthyError()

    return installed_app


async def is_healthy(
    app_api_client: AppsApiClient,
    installed_app: InstalledApp,
) -> bool:
    try:
        apps_api_response = await app_api_client.get_by_id(app_id=installed_app.app_id)
    except NotFound:
        return False
    return apps_api_response["state"] in HEALTHY_STATUSES


async def get_app_url(
    apps_api_client: AppsApiClient, installed_app: InstalledApp
) -> str:
    if installed_app.url is not None:
        return installed_app.url
    try:
        outputs = await apps_api_client.get_outputs(installed_app.app_id)
    except AppsApiError:
        raise AppMissingUrlError()

    try:
        installed_app.url = url = outputs["external_web_app_url"]["host"]
    except KeyError:
        raise AppMissingUrlError()

    return cast(str, url)


async def app_from_request(
    request: Request,
    launchpad_app_name: str,
) -> T_App:
    app_class = APPS.get(launchpad_app_name)
    if not app_class:
        raise AppTemplateNotFound()

    app_context_class = APPS_CONTEXT[launchpad_app_name]
    app_context = await app_context_class.from_request(request=request)
    return app_class(context=app_context)
