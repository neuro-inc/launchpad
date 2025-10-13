import logging
from typing import Any

from fastapi import APIRouter
from fastapi_pagination import Page, paginate
from starlette.requests import Request
from starlette.status import HTTP_200_OK

from launchpad.app import Launchpad
from launchpad.apps.resources import (
    GenericAppInstallRequest,
    ImportAppRequest,
    ImportTemplateRequest,
    LaunchpadAppRead,
    LaunchpadInstalledAppRead,
    LaunchpadTemplateRead,
)
from launchpad.apps.service import (
    AppNotInstalledError,
    AppServiceError,
    AppTemplateNotFound,
    AppUnhealthyError,
    DepAppService,
)
from launchpad.apps.template_storage import insert_template, list_templates
from launchpad.auth.dependencies import AdminAuth, Auth
from launchpad.errors import BadRequest, NotFound
from launchpad.ext.apps_api import NotFound as AppsApiNotFound


logger = logging.getLogger(__name__)

apps_router = APIRouter()


@apps_router.get("", response_model=Page[LaunchpadAppRead])
async def view_get_apps_pool(
    request: Request,
) -> Any:
    """
    Get the pool of available app templates.

    Returns all non-internal templates from the AppTemplate table.
    """
    logger.info("GET /api/v1/apps - Fetching app pool (non-internal templates)")

    app: Launchpad = request.app

    async with app.db() as db:
        # Get all non-internal templates
        templates = await list_templates(db, is_internal=False)
        logger.info(f"Retrieved {len(templates)} non-internal templates from storage")

    # Convert AppTemplate to LaunchpadAppRead
    app_reads = [
        LaunchpadAppRead.model_validate(
            {
                "verbose_name": template.verbose_name,
                "name": template.name,
                "description_short": template.description_short,
                "description_long": template.description_long,
                "logo": template.logo,
                "documentation_urls": template.documentation_urls,
                "external_urls": template.external_urls,
                "tags": template.tags,
            }
        )
        for template in templates
    ]

    logger.info(f"Converted to {len(app_reads)} LaunchpadAppRead objects")
    result = paginate(app_reads)
    logger.info("Returning paginated result")
    return result


@apps_router.post(
    "/install",
    status_code=HTTP_200_OK,
    response_model=LaunchpadInstalledAppRead,
)
async def view_post_install_generic_app(
    request: Request,
    generic_app_request: GenericAppInstallRequest,
    app_service: DepAppService,
    user: Auth,
) -> Any:
    """
    Install a generic app with custom template and configuration.

    This endpoint:
    1. Creates/updates an AppTemplate record with the provided metadata
    2. Installs the app using that template

    Example request body:
    ```json
    {
        "template_name": "my-template",
        "template_version": "1.0.0",
        "inputs": {
            "displayName": "My Custom App",
            "preset": {"name": "cpu-small"},
            "custom_config": {"key": "value"}
        },
        "name": "my-custom-app",
        "verbose_name": "My Custom App",
        "description_short": "A custom application",
        "logo": "https://example.com/logo.png"
    }
    ```
    """

    app: Launchpad = request.app

    # Create or update the template
    async with app.db() as db:
        async with db.begin():
            await insert_template(
                db=db,
                name=generic_app_request.name or generic_app_request.template_name,
                template_name=generic_app_request.template_name,
                template_version=generic_app_request.template_version,
                verbose_name=generic_app_request.verbose_name
                or generic_app_request.name
                or generic_app_request.template_name,
                description_short=generic_app_request.description_short,
                description_long=generic_app_request.description_long,
                logo=generic_app_request.logo,
                documentation_urls=generic_app_request.documentation_urls,
                external_urls=generic_app_request.external_urls,
                tags=generic_app_request.tags,
                is_internal=generic_app_request.is_internal,
                is_shared=generic_app_request.is_shared,
                handler_class=None,  # No handler for generic apps
                default_inputs=generic_app_request.inputs,
            )

    # Install from the template
    try:
        template_name = generic_app_request.name or generic_app_request.template_name
        return await app_service.install_from_template(
            request=request,
            template_name=template_name,
            user_inputs=None,  # Already in default_inputs
            user_id=user.id,
        )
    except AppServiceError as e:
        raise BadRequest(str(e))


@apps_router.post(
    "/import",
    status_code=HTTP_200_OK,
    response_model=LaunchpadInstalledAppRead,
)
async def view_post_import_app(
    request: Request,
    import_request: ImportAppRequest,
    app_service: DepAppService,
    user: AdminAuth,
) -> Any:
    """
    Import an externally installed app from Apps API.

    This endpoint:
    1. Fetches app instance details from Apps API
    2. Fetches template metadata from Apps API
    3. Creates/updates AppTemplate with the metadata
    4. Links the existing app installation to the template

    You can override metadata when importing.

    Example request body:
    ```json
    {
        "app_id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "my-imported-app",
        "verbose_name": "My Imported App",
        "description_short": "An externally installed app",
        "logo": "https://example.com/logo.png"
    }
    ```
    """
    try:
        return await app_service.import_app(import_request)
    except AppServiceError as e:
        raise BadRequest(str(e))


@apps_router.post(
    "/templates/import",
    status_code=HTTP_200_OK,
    response_model=LaunchpadTemplateRead,
)
async def view_post_import_template(
    request: Request,
    import_request: ImportTemplateRequest,
    app_service: DepAppService,
    user: AdminAuth,
) -> Any:
    """
    Import a template from Apps API to make it available in the app pool.

    This endpoint:
    1. Fetches template metadata from Apps API
    2. Creates/updates AppTemplate record
    3. Does NOT install the app (just adds template to pool)

    You can configure whether apps from this template are shared and override metadata.

    Example request body:
    ```json
    {
        "template_name": "my-template",
        "template_version": "1.0.0",
        "is_shared": false,
        "name": "my-custom-name",
        "verbose_name": "My Custom Template",
        "description_short": "A custom template"
    }
    ```
    """
    try:
        return await app_service.import_template(import_request)
    except AppServiceError as e:
        raise BadRequest(str(e))


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
    """
    Install or get an app by template name.

    If the app is not installed, it will be installed using the template from AppTemplate table.
    If the app is already installed, returns the existing installation.
    This endpoint is safe for polling - it will not create duplicate installations.
    """
    logger.info(f"POST /api/v1/apps/{app_name} - user_id={user.id}")

    try:
        installed_app = await app_service.get_installed_app(
            launchpad_app_name=app_name,
            user_id=user.id,
        )
    except AppsApiNotFound:
        logger.error(f"App {app_name} not found in Apps API")
        raise NotFound(f"Unknown app {app_name}")
    except AppNotInstalledError:
        # App not found in DB or not healthy - check if installation is in progress
        logger.info(
            f"App {app_name} not installed, checking for in-progress installation"
        )

        # Check if app exists in DB (regardless of health status) to prevent duplicate installations
        existing_app = await app_service.get_existing_app(
            launchpad_app_name=app_name,
            user_id=user.id,
        )

        if existing_app:
            logger.info(
                f"App {app_name} found in DB (app_id={existing_app.app_id}), "
                f"returning existing installation to prevent duplicate"
            )
            return existing_app

        # Truly not installed, proceed with installation
        logger.info(f"App {app_name} not found, attempting to install from template")
        try:
            return await app_service.install_from_template(
                request, app_name, user_id=user.id
            )
        except AppTemplateNotFound:
            logger.error(f"App template {app_name} not found in database")
            raise NotFound(f"App template {app_name} does not exist in the pool")
        except AppServiceError as e:
            logger.error(f"Error installing app {app_name}: {e}")
            raise BadRequest(str(e))

    except AppUnhealthyError as e:
        # App exists but is unhealthy - check if it's just being installed
        logger.warning(f"App {app_name} is unhealthy (app_id={e.app_id})")

        # Get the app from DB to return its current state
        existing_app = await app_service.get_existing_app(
            launchpad_app_name=app_name,
            user_id=user.id,
        )

        if existing_app:
            logger.info(f"Returning unhealthy app {app_name} for status polling")
            return existing_app

        raise BadRequest(f"App {app_name} is unhealthy")
    else:
        logger.info(
            f"App {app_name} already installed, returning existing installation"
        )
        return installed_app
