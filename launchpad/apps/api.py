from typing import Any

from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination import paginate
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_202_ACCEPTED, HTTP_303_SEE_OTHER

from launchpad.apps.registry import APPS
from launchpad.apps.resources import LaunchpadAppRead
from launchpad.apps.service import (
    app_from_request,
    AppTemplateNotFound,
    get_app_url,
    AppMissingUrlError,
)
from launchpad.apps.storage import insert_app, select_app
from launchpad.db.dependencies import Db
from launchpad.errors import NotFound

apps_router = APIRouter()


def redirect(to: str) -> Response:
    return Response(status_code=HTTP_303_SEE_OTHER, headers={"Location": to})


@apps_router.get("", response_model=Page[LaunchpadAppRead])
async def view_get_apps_pool() -> Any:
    return paginate(list(APPS.values()))


@apps_router.post(
    "/{app_name}",
    status_code=HTTP_202_ACCEPTED,
)
async def view_post_run_app(
    request: Request,
    db: Db,
    app_name: str,
) -> Any:
    apps_api_client = request.app.apps_api_client

    # first we check if app is already running, maybe we should just return an app URL
    async with db.begin():
        existing_app = await select_app(db, name=app_name)
        if existing_app is not None:
            try:
                url = await get_app_url(apps_api_client, installed_app=existing_app)
            except AppMissingUrlError:
                return Response(status_code=HTTP_202_ACCEPTED)
            else:
                return redirect(to=url)

    # app is not running yet, lets generated app and install it
    try:
        app = await app_from_request(request, app_name)
    except AppTemplateNotFound:
        raise NotFound(f"App {app_name} does not exist in the pool")

    installation_response = await apps_api_client.install_app(
        payload=await app.to_apps_api_payload()
    )

    async with db.begin():
        await insert_app(
            db=db,
            app_id=installation_response["id"],
            app_name=installation_response["name"],
            launchpad_app_name=app.name,
            is_internal=app.is_internal,
            is_shared=app.is_shared,
            user_id=None,
            url=None,
        )

    return Response(status_code=HTTP_202_ACCEPTED)
