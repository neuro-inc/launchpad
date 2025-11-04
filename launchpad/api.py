import logging
from typing import Any

from fastapi import APIRouter
from fastapi.params import Depends
from starlette.requests import Request
from starlette.responses import Response

from launchpad.app import Launchpad
from launchpad.apps.api import apps_router
from launchpad.auth.api import auth_router
from launchpad.auth.dependencies import auth_required


logger = logging.getLogger(__name__)

root_router = APIRouter()

api_v1_router = APIRouter(dependencies=[Depends(auth_required)])


api_v1_router.include_router(apps_router, prefix="/apps")
root_router.include_router(auth_router, prefix="/auth")


root_router.include_router(
    api_v1_router,
    prefix="/api/v1",
)


@root_router.get("/ping")
async def ping() -> Response:
    return Response("Pong", status_code=200)


@root_router.get("/config")
async def view_get_config(request: Request) -> dict[str, Any]:
    app: Launchpad = request.app
    return {
        "keycloak": {
            "url": str(app.config.keycloak.url),
            "realm": app.config.keycloak.realm,
        }
    }
