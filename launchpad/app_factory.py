from typing import Any, TypedDict

from fastapi.responses import ORJSONResponse
from fastapi_pagination import add_pagination
from starlette.responses import JSONResponse

from launchpad.api import root_router
from launchpad.app import App
from launchpad.config import Config
from launchpad.lifespan import lifespan


class AppConfig(TypedDict):
    default_response_class: type[JSONResponse]
    openapi_url: str | None
    docs_url: str | None
    redoc_url: str | None
    lifespan: Any
    redirect_slashes: bool


def create_app(config: Config) -> App:
    app_kwargs: AppConfig = {
        "default_response_class": ORJSONResponse,
        "openapi_url": "/openapi/openapi.json",
        "docs_url": "/openapi/v1/docs",
        "redoc_url": "/openapi/v1/redoc",
        "lifespan": lifespan,
        "redirect_slashes": False,
    }

    app = App(**app_kwargs)
    app.config = config
    app.include_router(root_router)
    add_pagination(app)
    return app
