from fastapi import APIRouter
from starlette.responses import Response

root_router = APIRouter()


@root_router.get("/ping")
async def ping() -> Response:
    return Response("Pong", status_code=200)
