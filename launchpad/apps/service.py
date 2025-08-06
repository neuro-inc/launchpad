import logging
from typing import Any, Annotated
from uuid import UUID

from fastapi import Depends
from starlette.requests import Request

from launchpad.app import Launchpad
from launchpad.apps.models import InstalledApp
from launchpad.apps.registry import APPS, APPS_CONTEXT, T_App, USER_FACING_APPS
from launchpad.apps.storage import select_app, insert_app, delete_app
from launchpad.errors import BadRequest
from launchpad.ext.apps_api import NotFound, AppsApiError


logger = logging.getLogger(__name__)


HEALTHY_STATUSES = {"queued", "progressing", "healthy"}


class AppServiceError(Exception): ...


class AppNotInstalledError(AppServiceError): ...


class AppUnhealthyError(AppServiceError):
    def __init__(self, app_id: UUID):
        self.app_id = app_id


class AppTemplateNotFound(AppServiceError): ...


class AppMissingUrlError(AppServiceError): ...


class AppService:
    def __init__(self, app: Launchpad):
        self._db = app.db
        self._apps_api_client = app.apps_api_client

    async def get_installed_app(
        self,
        launchpad_app_name: str,
        user_id: str | None = None,
        *,
        with_url: bool = True,
    ) -> InstalledApp:
        try:
            app_class = APPS[launchpad_app_name]
        except KeyError:
            raise NotFound(f"Unknown app {launchpad_app_name}")

        select_params: dict[str, Any] = {"name": launchpad_app_name}
        if not app_class.is_shared and not app_class.is_internal:
            # personal app, let's add user ID to a selection and validate it exists.
            if user_id is None:
                raise BadRequest("Access to a personal app without user ID provided")
            select_params["user_id"] = user_id

        async with self._db() as db:
            installed_app = await select_app(db, **select_params)

        if installed_app is None:
            raise AppNotInstalledError()

        if not await self.is_healthy(installed_app):
            raise AppUnhealthyError(installed_app.app_id)

        if with_url and installed_app.url is None:
            # an app doesn't have a URL yet, so let's try to get it from the outputs
            try:
                outputs = await self._apps_api_client.get_outputs(installed_app.app_id)
            except AppsApiError:
                logger.info(f"App {launchpad_app_name} has not yet pushed outputs")
            else:
                try:
                    async with self._db() as db:
                        async with db.begin():
                            output_url = outputs["external_web_app_url"]
                            installed_app.url = (
                                f"{output_url['protocol']}://{output_url['host']}"
                            )
                except KeyError:
                    logger.error(
                        f"App {launchpad_app_name} does not declare external web app url"
                    )

        return installed_app

    async def install_from_request(
        self,
        request: Request,
        launchpad_app_name: str,
    ) -> InstalledApp:
        app = await self._app_from_request(request, launchpad_app_name)
        return await self.install(app=app)

    async def install(
        self,
        app: T_App,
    ) -> InstalledApp:
        async with self._db() as db:
            async with db.begin():
                installation_response = await self._apps_api_client.install_app(
                    payload=await app.to_apps_api_payload()
                )
                return await insert_app(
                    db=db,
                    app_id=installation_response["id"],
                    app_name=installation_response["name"],
                    launchpad_app_name=app.name,
                    is_internal=app.is_internal,
                    is_shared=app.is_shared,
                    user_id=None,
                    url=None,
                )

    async def delete(self, app_id: UUID) -> None:
        await self._apps_api_client.delete_app(app_id)
        async with self._db() as db:
            async with db.begin():
                await delete_app(db, app_id)

    async def is_healthy(
        self,
        installed_app: InstalledApp,
    ) -> bool:
        try:
            apps_api_response = await self._apps_api_client.get_by_id(
                app_id=installed_app.app_id
            )
        except NotFound:
            return False
        return apps_api_response["state"] in HEALTHY_STATUSES

    @staticmethod
    async def _app_from_request(
        request: Request,
        launchpad_app_name: str,
    ) -> T_App:
        app_class = USER_FACING_APPS.get(launchpad_app_name)
        if not app_class:
            raise AppTemplateNotFound()

        app_context_class = APPS_CONTEXT[launchpad_app_name]
        app_context = await app_context_class.from_request(request=request)
        return app_class(context=app_context)


async def dep_app_service(request: Request) -> AppService:
    app: Launchpad = request.app
    return app.app_service


DepAppService = Annotated[AppService, Depends(dep_app_service)]
