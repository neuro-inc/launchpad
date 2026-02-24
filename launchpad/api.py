import logging
from functools import cache
from pathlib import Path
from typing import Any

import magic
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from starlette.requests import Request
from starlette.responses import FileResponse, Response

from launchpad.app import Launchpad
from launchpad.apps.api import apps_router
from launchpad.auth.api import auth_router
from launchpad.auth.dependencies import auth_required


logger = logging.getLogger(__name__)


@cache
def detect_media_type(file_path: Path, default: str) -> str:
    try:
        mime = magic.Magic(mime=True)
        detected_type = mime.from_file(str(file_path))
        if detected_type:
            return detected_type
    except Exception as e:
        logger.warning(f"Failed to detect file type for {file_path}: {e}")
    return default


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

    # Check if custom branding files exist
    branding_dir = app.config.branding.branding_dir
    logo_exists = (branding_dir / "logo").exists()
    favicon_exists = (branding_dir / "favicon").exists()
    background_exists = (branding_dir / "background").exists()

    # Build branding URLs
    base_url = str(request.url_for("view_get_config")).rsplit("/config", 1)[0]
    logo_url = f"{base_url}/branding/logo" if logo_exists else None
    favicon_url = f"{base_url}/branding/favicon" if favicon_exists else None
    background_url = f"{base_url}/branding/background" if background_exists else None

    return {
        "keycloak": {
            "url": str(app.config.keycloak.url),
            "realm": app.config.keycloak.realm,
        },
        "branding": {
            "logo_url": logo_url,
            "favicon_url": favicon_url,
            "background_url": background_url,
            "title": app.config.branding.title,
            "background": app.config.branding.background,
        },
    }


@root_router.get("/branding/logo")
async def get_branding_logo(request: Request) -> FileResponse:
    app: Launchpad = request.app
    logo_path = app.config.branding.branding_dir / "logo"

    if not logo_path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")

    media_type = detect_media_type(file_path=logo_path, default="image/svg+xml")

    return FileResponse(
        path=logo_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@root_router.get("/branding/favicon")
async def get_branding_favicon(request: Request) -> FileResponse:
    app: Launchpad = request.app
    favicon_path = app.config.branding.branding_dir / "favicon"

    if not favicon_path.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")

    media_type = detect_media_type(file_path=favicon_path, default="image/x-icon")

    return FileResponse(
        path=favicon_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@root_router.get("/branding/background")
async def get_branding_background(request: Request) -> FileResponse:
    app: Launchpad = request.app
    background_path = app.config.branding.branding_dir / "background"

    if not background_path.exists():
        raise HTTPException(status_code=404, detail="Background not found")

    media_type = detect_media_type(file_path=background_path, default="image/png")

    return FileResponse(
        path=background_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
