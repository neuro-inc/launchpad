from typing import Any

from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination import paginate
from starlette.requests import Request
from starlette.status import HTTP_200_OK

from launchpad.apps.registry import APPS
from launchpad.apps.resources import LaunchpadAppRead, LaunchpadInstalledAppRead
from launchpad.apps.service import (
    AppTemplateNotFound,
    DepAppService,
)
from launchpad.errors import NotFound

apps_router = APIRouter()


@apps_router.get("", response_model=Page[LaunchpadAppRead])
async def view_get_apps_pool() -> Any:
    return paginate(list(APPS.values()))


@apps_router.post(
    "/{app_name}",
    status_code=HTTP_200_OK,
    response_model=LaunchpadInstalledAppRead,
)
async def view_post_run_app(
    request: Request,
    app_name: str,
    app_service: DepAppService,
) -> Any:
    installed_app = await app_service.get_installed_app(launchpad_app_name=app_name)
    if installed_app is not None:
        return installed_app

    # app is not running yet, lets generated app and install it
    try:
        return await app_service.install_from_request(request, app_name)
    except AppTemplateNotFound:
        raise NotFound(f"App {app_name} does not exist in the pool")
