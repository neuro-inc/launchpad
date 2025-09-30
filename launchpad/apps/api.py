from typing import Any

from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination import paginate
from starlette.requests import Request
from starlette.status import HTTP_200_OK

from launchpad.apps.registry import USER_FACING_APPS
from launchpad.apps.resources import (
    GenericAppInstallRequest,
    ImportAppRequest,
    LaunchpadAppRead,
    LaunchpadInstalledAppRead,
)
from launchpad.apps.service import (
    AppTemplateNotFound,
    DepAppService,
    AppNotInstalledError,
    AppUnhealthyError,
    AppServiceError,
)
from launchpad.auth.dependencies import Auth
from launchpad.errors import NotFound, BadRequest
from launchpad.ext.apps_api import NotFound as AppsApiNotFound

apps_router = APIRouter()


@apps_router.get("", response_model=Page[LaunchpadAppRead])
async def view_get_apps_pool(
    app_service: DepAppService,
) -> Any:
    """
    Get the pool of available apps.

    Returns both predefined user-facing apps and installed generic apps.
    """
    # Get predefined apps
    predefined_apps = list(USER_FACING_APPS.values())

    # Get installed generic apps (those not in the predefined registry)
    installed_apps = await app_service.list_installed_apps()
    generic_apps = [
        app for app in installed_apps if app.launchpad_app_name not in USER_FACING_APPS
    ]

    # Convert InstalledApp to LaunchpadAppRead format
    generic_app_reads = [
        LaunchpadAppRead.model_validate(
            {
                "verbose_name": app.verbose_name,
                "name": app.launchpad_app_name,
                "description_short": app.description_short,
                "description_long": app.description_long,
                "logo": app.logo,
                "documentation_urls": app.documentation_urls,
                "external_urls": app.external_urls,
                "tags": app.tags,
            }
        )
        for app in generic_apps
    ]

    # Combine predefined apps and generic apps
    all_apps = predefined_apps + generic_app_reads

    return paginate(all_apps)


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

    This endpoint allows installing any app template by providing:
    - template_name: The name of the template to install
    - template_version: The version of the template
    - inputs: The inputs to pass to the Apps API
    - Optional metadata: name, verbose_name, description, logo, etc.

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
    try:
        return await app_service.install_from_request(
            request=request,
            generic_app_request=generic_app_request,
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
    user: Auth,
) -> Any:
    """
    Import an externally installed app from Apps API.

    This endpoint allows importing apps that were installed outside of Launchpad
    by providing their app_id. The server will query Apps API to retrieve the app's
    template information and store it in Launchpad's database.

    You can override metadata when importing:
    - name: Custom launchpad app name
    - verbose_name: User-friendly display name
    - description_short: Short description
    - description_long: Long description
    - logo: URL to logo
    - documentation_urls: List of documentation URLs
    - external_urls: List of external URLs
    - tags: List of tags

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
    try:
        installed_app = await app_service.get_installed_app(
            launchpad_app_name=app_name,
            user_id=user.id,
        )
    except AppsApiNotFound:
        raise NotFound(f"Unknown app {app_name}")
    except AppNotInstalledError:
        # app is not running yet, lets do an installation
        try:
            return await app_service.install_from_request(request, app_name)
        except AppTemplateNotFound:
            raise NotFound(f"App {app_name} does not exist in the pool")
        except AppServiceError as e:
            raise BadRequest(str(e))

    except AppUnhealthyError:
        raise BadRequest(f"App {app_name} is unhealthy")
    else:
        return installed_app
