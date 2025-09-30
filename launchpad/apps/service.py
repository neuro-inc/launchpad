import asyncio
import logging
from typing import Any, Annotated
from uuid import UUID

import backoff
from fastapi import Depends
from starlette.requests import Request

from launchpad.app import Launchpad
from launchpad.apps.models import InstalledApp
from launchpad.apps.registry import APPS, APPS_CONTEXT, T_App, USER_FACING_APPS
from launchpad.apps.storage import (
    select_app,
    insert_app,
    delete_app,
    update_app_url,
    list_apps,
)
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
        self._instance_id = app.config.instance_id
        self._output_buffer: asyncio.Queue[InstalledApp] = asyncio.Queue()

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
                    output_url = outputs["app_url"]["external_url"]
                    url = f"{output_url['protocol']}://{output_url['host']}"

                    # Update the URL in the database
                    async with self._db() as db:
                        async with db.begin():
                            updated_app = await update_app_url(
                                db, installed_app.app_id, url
                            )
                            if updated_app:
                                installed_app.url = url
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

    @backoff.on_exception(
        wait_gen=backoff.expo,
        exception=(
            AppServiceError,
            AppsApiError,
        ),
        max_tries=5,
    )
    async def _batch_append_apps_to_outputs(
        self,
        apps: list[InstalledApp],
    ) -> None:
        if self._instance_id is None:
            raise AppServiceError("Instance ID is not configured")

        outputs = None
        try:
            outputs = await self._apps_api_client.get_outputs(self._instance_id)
        except Exception as e:
            logger.info(f"Failed to get outputs for instance {self._instance_id}: {e}")

        if outputs is None:
            raise AppServiceError(
                "No outputs exist for instance. Cannot append apps until post-outputs hook creates initial outputs."
            )

        installed_apps = outputs.get("installed_apps", {})
        app_list = installed_apps.get("app_list", [])

        # Get existing app IDs to avoid duplicates
        existing_app_ids = {UUID(a["app_id"]) for a in app_list if "app_id" in a}

        # Add all new apps in batch
        for app in apps:
            if app.app_id not in existing_app_ids:
                app_list.append(
                    {
                        "app_id": str(app.app_id),
                        "app_name": app.app_name,
                    }
                )

        installed_apps["app_list"] = app_list
        outputs["installed_apps"] = installed_apps

        try:
            await self._apps_api_client.update_outputs(
                self._instance_id,
                outputs,
            )
        except AppsApiError as e:
            logger.error(
                f"Failed to update outputs for instance {self._instance_id}: {e}"
            )
            raise AppServiceError("Failed to update instance outputs") from e

    async def _add_app_to_buffer(self, app: InstalledApp) -> None:
        """Add an app to the output buffer for later processing."""
        await self._output_buffer.put(app)
        logger.debug(f"Added app {app.app_id} to output buffer")

    async def process_output_buffer(self) -> None:
        """Process all apps in the output buffer and update outputs in a single batch."""
        processed_apps = []

        # Collect all apps from the buffer
        while not self._output_buffer.empty():
            try:
                app = self._output_buffer.get_nowait()
                processed_apps.append(app)
            except asyncio.QueueEmpty:
                break

        if not processed_apps:
            return

        logger.info(
            f"Processing {len(processed_apps)} apps from output buffer in batch"
        )

        # Batch process all apps with a single outputs update
        try:
            await self._batch_append_apps_to_outputs(processed_apps)
            logger.info(f"Successfully processed {len(processed_apps)} apps in batch")
        except Exception as e:
            logger.error(f"Failed to batch process apps from buffer: {e}")
            # Re-add all apps to buffer for retry on next cycle
            for app in processed_apps:
                await self._output_buffer.put(app)

    async def install(
        self,
        app: T_App,
    ) -> InstalledApp:
        installed_app = None
        async with self._db() as db:
            async with db.begin():
                payload = None
                try:
                    payload = await app.to_apps_api_payload()
                    installation_response = await self._apps_api_client.install_app(
                        payload=payload
                    )
                except AppsApiError:
                    logger.exception("Apps API error occurred")
                    logger.error(f"Failed payload: {payload}")
                    raise AppServiceError(
                        "Internal service error. "
                        "Please try again later, or contact support"
                    )
                installed_app = await insert_app(
                    db=db,
                    app_id=installation_response["id"],
                    app_name=installation_response["name"],
                    launchpad_app_name=app.name,
                    is_internal=app.is_internal,
                    is_shared=app.is_shared,
                    user_id=None,
                    url=None,
                )

        await self._add_app_to_buffer(installed_app)
        return installed_app

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

    async def list_installed_apps(
        self,
        user_id: str | None = None,
    ) -> list[InstalledApp]:
        async with self._db() as db:
            return list(await list_apps(db, user_id=user_id))


async def dep_app_service(request: Request) -> AppService:
    app: Launchpad = request.app
    return app.app_service


DepAppService = Annotated[AppService, Depends(dep_app_service)]
