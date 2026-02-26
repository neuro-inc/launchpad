import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi_pagination import Page, paginate
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from launchpad.app import Launchpad
from launchpad.apps.exceptions import (
    AppNotInstalledError,
    AppServiceError,
    AppTemplateNotFound,
    AppUnhealthyError,
)
from launchpad.apps.models import InstalledApp
from launchpad.apps.resources import (
    GenericAppInstallRequest,
    ImportAppRequest,
    ImportTemplateRequest,
    LaunchpadAppRead,
    LaunchpadInstalledAppRead,
    LaunchpadTemplateRead,
)
from launchpad.apps.service import DepAppService
from launchpad.auth.dependencies import AdminAuth, Auth
from launchpad.errors import BadRequest, NotFound
from launchpad.ext.apps_api import NotFound as AppsApiNotFound


logger = logging.getLogger(__name__)

apps_router = APIRouter()


@apps_router.get("", response_model=Page[LaunchpadAppRead])
async def view_get_apps_pool(
    app_service: DepAppService,
) -> Any:
    """
    Get the pool of available app templates.

    Returns all non-internal templates from the AppTemplate table.
    """
    logger.info("GET /api/v1/apps - Fetching app pool (non-internal templates)")

    # Get all non-internal templates
    app_reads = await app_service.list_app_pool(is_internal=False)
    logger.info(f"Retrieved {len(app_reads)} non-internal templates")

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

    # Create or update the template
    await app_service.create_or_update_template(
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
        input=generic_app_request.inputs,
    )

    # Install from the template
    try:
        template_name = generic_app_request.name or generic_app_request.template_name
        return await app_service.install_from_template(
            request=request,
            template_name=template_name,
            user_inputs=None,  # Already in input
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


@apps_router.get("/templates", response_model=Page[LaunchpadTemplateRead])
async def view_get_templates(
    request: Request,
    user: AdminAuth,
    is_internal: bool | None = None,
) -> Any:
    """
    Get all app templates.

    This endpoint requires admin authentication.
    Returns a paginated list of all templates in the system.

    Query parameters:
    - is_internal: Optional filter to get only internal or non-internal templates
    """
    app: Launchpad = request.app
    async with app.db() as db:
        from launchpad.apps.template_storage import list_templates

        templates = await list_templates(db, is_internal=is_internal)
        print("TEMPLATES FETCHED:")
        print(templates)
        template_reads = [
            LaunchpadTemplateRead.model_validate(template) for template in templates
        ]
        return paginate(template_reads)


@apps_router.get("/instances", response_model=Page[InstalledApp])
async def view_get_instances(
    app_service: DepAppService,
    user: AdminAuth,
) -> Any:
    """
    Get all installed app instances.

    This endpoint requires admin authentication.
    Returns a paginated list of all installed apps across all users.
    """
    installed_apps = await app_service.list_installed_apps()
    return paginate(installed_apps)


@apps_router.get("/instances/unimported")
async def view_get_unimported_instances(
    app_service: DepAppService,
    user: AdminAuth,
    page: int = 1,
    size: int = 50,
) -> dict[str, Any]:
    """
    Get healthy app instances from Apolo that haven't been imported into Launchpad yet.

    This endpoint requires admin authentication.
    Returns a paginated list of healthy app instances that exist in Apps API
    but are not yet tracked in Launchpad's database.

    Only instances with state="healthy" are returned.

    Query parameters:
    - page: Page number (default: 1)
    - size: Page size (default: 50, max: 100)

    Returns:
    - items: List of unimported healthy app instances
    - total: Total count of unimported healthy instances
    - page: Current page number
    - size: Page size
    - pages: Total number of pages

    Example response:
    ```json
    {
        "items": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "my-app-abc123",
                "template_name": "jupyter",
                "template_version": "1.0.0",
                "display_name": "My Jupyter Notebook",
                "state": "healthy",
                "created_at": "2025-01-15T10:30:00Z",
                ...
            }
        ],
        "total": 5,
        "page": 1,
        "size": 50,
        "pages": 1
    }
    ```
    """
    try:
        return await app_service.list_unimported_instances(page=page, size=size)
    except AppServiceError as e:
        raise BadRequest(str(e))


@apps_router.delete("/templates/{template_id}", status_code=HTTP_204_NO_CONTENT)
async def view_delete_template(
    template_id: UUID,
    app_service: DepAppService,
    user: AdminAuth,
) -> None:
    """
    Delete a template by its ID.

    This endpoint requires admin authentication.
    Deletes the template from the AppTemplate table.
    """
    await app_service.delete_template_by_id(template_id)


@apps_router.delete("/instances/{app_id}", status_code=HTTP_204_NO_CONTENT)
async def view_delete_instance(
    app_id: UUID,
    app_service: DepAppService,
    user: AdminAuth,
    uninstall: bool = True,
) -> None:
    """
    Delete an app instance by its ID.

    This endpoint requires admin authentication.
    Uninstalls the app from Apps API (if uninstall=True) and removes it from the database.
    """
    await app_service.delete(app_id, uninstall=uninstall)
