from typing import Any, TypedDict

from fastapi.responses import ORJSONResponse
from fastapi_pagination import add_pagination
from fastapi_pagination.utils import disable_installed_extensions_check
from starlette.responses import JSONResponse

from launchpad.api import root_router
from launchpad.app import Launchpad
from launchpad.config import Config
from launchpad.db.sync import sync_db
from launchpad.lifespan import lifespan


class AppConfig(TypedDict):
    default_response_class: type[JSONResponse]
    openapi_url: str | None
    docs_url: str | None
    redoc_url: str | None
    lifespan: Any
    redirect_slashes: bool


def create_app(config: Config) -> Launchpad:
    # keep db up to date by running migrations
    sync_db(dsn=config.postgres.dsn)

    app_kwargs: AppConfig = {
        "default_response_class": ORJSONResponse,
        "openapi_url": "/openapi/openapi.json",
        "docs_url": "/openapi/v1/docs",
        "redoc_url": "/openapi/v1/redoc",
        "lifespan": lifespan,
        "redirect_slashes": False,
    }

    app = Launchpad(**app_kwargs)
    app.config = config
    app.include_router(root_router)
    add_pagination(app)
    disable_installed_extensions_check()  # disable pagination warnings
    return app
