from typing import Any

from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination import paginate
from starlette.requests import Request
from starlette.status import HTTP_200_OK

from launchpad.apps.registry import USER_FACING_APPS
from launchpad.apps.resources import LaunchpadAppRead, LaunchpadInstalledAppRead
from launchpad.apps.service import (
    AppTemplateNotFound,
    DepAppService,
    AppNotInstalledError,
    AppUnhealthyError,
)
from launchpad.auth.dependencies import Auth
from launchpad.errors import NotFound

apps_router = APIRouter()


@apps_router.get("", response_model=Page[LaunchpadAppRead])
async def view_get_apps_pool() -> Any:
    return paginate(list(USER_FACING_APPS.values()))


@apps_router.post(
    "/{app_name}",
    status_code=HTTP_200_OK,
    response_model=LaunchpadInstalledAppRead,
)
async def view_post_run_app(
    request: Request,
    app_name: str,
    app_service: DepAppService,
    user: Auth,
) -> Any:
    try:
        installed_app = await app_service.get_installed_app(
            launchpad_app_name=app_name,
            user_id=user.id,
        )
    except AppNotInstalledError:
        # app is not running yet, lets generated app and install it
        try:
            return await app_service.install_from_request(request, app_name)
        except AppTemplateNotFound:
            raise NotFound(f"App {app_name} does not exist in the pool")

    except AppUnhealthyError as e:
        # an app exists, but it is not healthy. let's try to re-install
        await app_service.delete(e.app_id)
        return await app_service.install_from_request(request, app_name)

    else:
        return installed_app
