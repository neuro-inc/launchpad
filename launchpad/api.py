from fastapi import APIRouter
from starlette.responses import Response

from launchpad.apps.api import apps_router

root_router = APIRouter()
api_v1_router = APIRouter()


api_v1_router.include_router(apps_router, prefix="/apps")

root_router.include_router(
    api_v1_router,
    prefix="/api/v1",
)


@root_router.get("/ping")
async def ping() -> Response:
    return Response("Pong", status_code=200)
