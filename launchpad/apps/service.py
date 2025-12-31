import asyncio
import logging
from typing import TYPE_CHECKING, Annotated, Any, Any as AnyType, cast
from uuid import UUID

import backoff
from fastapi import Depends
from starlette.requests import Request


if TYPE_CHECKING:
    from launchpad.app import Launchpad

from launchpad.apps.exceptions import (
    AppMissingUrlError,
    AppNotInstalledError,
    AppServiceError,
    AppTemplateNotFound,
    AppUnhealthyError,
)
from launchpad.apps.models import InstalledApp
from launchpad.apps.registry import (
    APPS_CONTEXT,
    HANDLER_CLASSES,
    USER_FACING_APPS,
    T_App,
)
from launchpad.apps.registry.base import GenericApp
from launchpad.apps.registry.internal.context import InternalAppContext
from launchpad.apps.resources import (
    ImportAppRequest,
    ImportTemplateRequest,
    LaunchpadAppRead,
)
from launchpad.apps.storage import (
    delete_app,
    insert_app,
    list_apps,
    select_app,
    update_app_endpoints,
    update_app_url,
)
from launchpad.apps.template_models import AppTemplate
from launchpad.apps.template_storage import (
    delete_template,
    insert_template,
    list_templates,
    select_template,
)
from launchpad.errors import BadRequest
from launchpad.ext.apps_api import AppsApiError, NotFound


logger = logging.getLogger(__name__)


HEALTHY_STATUSES = {"queued", "progressing", "healthy"}


class AppService:
    def __init__(self, app: "Launchpad"):
        self._db = app.db
        self._apps_api_client = app.apps_api_client
        self._instance_id = app.config.instance_id
        self._output_buffer: asyncio.Queue[InstalledApp] = asyncio.Queue()

    async def get_existing_app(
        self,
        launchpad_app_name: str,
        user_id: str | None = None,
    ) -> InstalledApp | None:
        """
        Check if an app exists in the database, regardless of its health status.
        This is useful for preventing duplicate installations during polling.

        Returns None if the app doesn't exist, otherwise returns the InstalledApp.
        Does NOT check health status or fetch URLs.
        """

        logger.info(
            f"get_existing_app called: app_name={launchpad_app_name}, user_id={user_id}"
        )

        # Check if template exists in database
        async with self._db() as db_template:
            template = await select_template(db_template, name=launchpad_app_name)

        if template is None:
            logger.warning(f"Template not found in database: {launchpad_app_name}")
            return None

        # Use template metadata to determine selection criteria
        select_params: dict[str, Any] = {"name": launchpad_app_name}
        if not template.is_shared and not template.is_internal:
            # personal app, let's add user ID to a selection
            if user_id is not None:
                select_params["user_id"] = user_id

        async with self._db() as db:
            installed_app = await select_app(db, **select_params)

        if installed_app:
            logger.info(
                f"Found existing app {launchpad_app_name}: "
                f"app_id={installed_app.app_id}"
            )
        else:
            logger.info(f"No existing app found for {launchpad_app_name}")

        return installed_app

    async def get_installed_app(
        self,
        launchpad_app_name: str,
        user_id: str | None = None,
        *,
        with_url: bool = True,
    ) -> InstalledApp:
        logger.info(
            f"get_installed_app called: app_name={launchpad_app_name}, "
            f"user_id={user_id}, with_url={with_url}"
        )

        # Check if template exists in database (replaces APPS registry check)
        async with self._db() as db_template:
            template = await select_template(db_template, name=launchpad_app_name)

        if template is None:
            logger.warning(f"Template not found in database: {launchpad_app_name}")
            raise NotFound(f"Unknown app {launchpad_app_name}")

        logger.info(
            f"Template found: {template.name} "
            f"(is_shared={template.is_shared}, is_internal={template.is_internal})"
        )

        # Use template metadata to determine selection criteria
        select_params: dict[str, Any] = {"name": launchpad_app_name}
        if not template.is_shared and not template.is_internal:
            # personal app, let's add user ID to a selection and validate it exists.
            if user_id is None:
                raise BadRequest("Access to a personal app without user ID provided")
            select_params["user_id"] = user_id

        logger.info(f"Checking if app is installed with params: {select_params}")

        async with self._db() as db:
            installed_app = await select_app(db, **select_params)

        if installed_app is None:
            logger.info(
                f"App {launchpad_app_name} not installed, raising AppNotInstalledError"
            )
            raise AppNotInstalledError()

        logger.info(
            f"App {launchpad_app_name} is installed: "
            f"app_id={installed_app.app_id}, url={installed_app.url}"
        )

        if not await self.is_healthy(installed_app):
            raise AppUnhealthyError(installed_app.app_id)

        if with_url and installed_app.url is None:
            # an app doesn't have a URL yet, so let's try to get it from the outputs
            try:
                url, external_url_list = await self._apps_api_client.get_app_endpoints(
                    installed_app.app_id
                )
                logger.info(
                    f"Fetched endpoints for app {launchpad_app_name}: "
                    f"url={url}, external_urls={len(external_url_list)}"
                )

                # Update the URL and external_url_list in the database
                async with self._db() as db:
                    async with db.begin():
                        updated_app = await update_app_endpoints(
                            db, installed_app.app_id, url, external_url_list
                        )
                        if updated_app:
                            installed_app.url = url
                            installed_app.external_url_list = external_url_list
            except AppsApiError:
                logger.info(
                    f"App {launchpad_app_name} has not yet pushed outputs, "
                    "url and external_url_list remain empty"
                )

        return installed_app

    async def install_from_template(
        self,
        request: Request,
        template_name: str,
        user_inputs: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> InstalledApp:
        """
        Install an app from an AppTemplate.

        This method:
        1. Fetches the template from the AppTemplate table
        2. Checks if the template has a handler_class
        3. If yes, uses that handler class; if no, uses GenericApp
        4. Merges input from template with user_inputs
        5. Installs the app

        Args:
            request: The HTTP request
            template_name: Name of the template from AppTemplate table
            user_inputs: Optional user-provided inputs to merge with template defaults
            user_id: User ID for non-shared apps (required if is_shared=False)

        Returns:
            The installed app

        Raises:
            AppTemplateNotFound: If template doesn't exist in database
            AppServiceError: If there's an error during installation
        """

        # Get template from database
        async with self._db() as db:
            template = await select_template(db, name=template_name)

        if not template:
            raise AppTemplateNotFound(f"Template {template_name} not found")

        # Validate user_id requirement for non-shared apps
        if not template.is_shared and not template.is_internal and user_id is None:
            raise AppServiceError(
                f"Cannot install non-shared app '{template_name}' without user_id"
            )

        # Merge inputs: user inputs override template defaults
        inputs = template.input.copy()
        if user_inputs:
            inputs.update(user_inputs)

        # Determine which app class to use
        app: T_App
        if template.handler_class and template.handler_class in HANDLER_CLASSES:
            # Use specific handler class

            app_class = cast(AnyType, HANDLER_CLASSES[template.handler_class])
            logger.info(f"App class selected: {app_class}")
            # Check if this handler needs special context
            if app_class.__name__ in APPS_CONTEXT:
                context_class = cast(AnyType, APPS_CONTEXT[app_class.__name__])
                ctx = await context_class.from_request(request=request)

                # Check if this is a GenericApp subclass or an App subclass
                if issubclass(app_class, GenericApp):
                    # GenericApp-based handlers need all parameters
                    app = app_class(
                        context=ctx,
                        template_name=template.template_name,
                        template_version=template.template_version,
                        inputs=inputs,
                        name=template.name,
                        is_internal=template.is_internal,
                        is_shared=template.is_shared,
                        verbose_name=template.verbose_name,
                        description_short=template.description_short,
                        description_long=template.description_long,
                        logo=template.logo,
                        documentation_urls=template.documentation_urls,
                        external_urls=template.external_urls,
                        tags=template.tags,
                    )
                else:
                    # App-based handlers (like OpenWebUIApp) only need context
                    app = app_class(context=ctx)
            else:
                # Handler without special context - use InternalAppContext

                internal_ctx = InternalAppContext(config=inputs)
                app = app_class(context=internal_ctx)
        else:
            # Use GenericApp for templates without handlers
            app = GenericApp(
                template_name=template.template_name,
                template_version=template.template_version,
                inputs=inputs,
                name=template.name,
                is_internal=template.is_internal,
                is_shared=template.is_shared,
                verbose_name=template.verbose_name,
                description_short=template.description_short,
                description_long=template.description_long,
                logo=template.logo,
                documentation_urls=template.documentation_urls,
                external_urls=template.external_urls,
                tags=template.tags,
            )

        app.user_id = user_id
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

        installed_apps = outputs.get("installed_apps") or {}
        app_list = installed_apps.get("app_list") or []

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
                    user_id=app.user_id,
                    url=None,
                    template_name=app.name,  # Reference to AppTemplate.name
                )

        await self._add_app_to_buffer(installed_app)
        return installed_app

    async def install_generic(
        self,
        template_name: str,
        template_version: str,
        inputs: dict[str, Any],
        name: str | None = None,
        is_internal: bool = False,
        is_shared: bool = True,
        verbose_name: str = "",
        description_short: str = "",
        description_long: str = "",
        logo: str = "",
        documentation_urls: list[dict[str, str]] | None = None,
        external_urls: list[dict[str, str]] | None = None,
        tags: list[str] | None = None,
        user_id: str | None = None,
    ) -> InstalledApp:
        """
        Install a generic app without requiring a predefined app class.

        Args:
            template_name: The name of the template to use for installation
            template_version: The version of the template
            inputs: The inputs to pass to the Apps API
            name: Optional name for the app (defaults to template_name)
            is_internal: Whether the app is internal (not visible to end users)
            is_shared: Whether the app can be shared by multiple users
            verbose_name: User-friendly name for the app
            description_short: Short description of the app
            description_long: Long description of the app
            logo: URL to the app's logo
            documentation_urls: List of documentation URLs
            external_urls: List of external URLs
            tags: List of tags for categorization

        Returns:
            The installed app record

        Example:
            ```python
            installed_app = await app_service.install_generic(
                template_name="my-template",
                template_version="1.0.0",
                inputs={
                    "displayName": "My App",
                    "preset": {"name": "cpu-small"},
                    "my_custom_input": "value"
                },
                name="my-app",
                is_shared=True
            )
            ```
        """
        generic_app = GenericApp(
            template_name=template_name,
            template_version=template_version,
            inputs=inputs,
            name=name,
            is_internal=is_internal,
            is_shared=is_shared,
            verbose_name=verbose_name,
            description_short=description_short,
            description_long=description_long,
            logo=logo,
            documentation_urls=documentation_urls,
            external_urls=external_urls,
            tags=tags,
        )
        generic_app.user_id = user_id
        return await self.install(generic_app)

    async def import_app(
        self,
        import_request: ImportAppRequest,
    ) -> InstalledApp:
        """
        Import an externally installed app by querying Apps API and storing it in the database.

        This method:
        1. Fetches the app instance details from Apps API
        2. Fetches the actual inputs used when the app was installed (for default_inputs)
        3. Fetches the template metadata (description, logo, tags, etc.)
        4. Uses the following priority for metadata:
           - User-provided overrides (from import_request)
           - Template metadata (from template definition)
           - Instance display_name (from app instance)
           - Defaults (empty strings/lists)

        Args:
            import_request: Import request containing app_id and optional metadata overrides

        Returns:
            The installed app record

        Raises:
            AppsApiError: If the app cannot be found or queried from Apps API
            AppServiceError: If there's an error storing the app

        Example:
            ```python
            installed_app = await app_service.import_app(
                ImportAppRequest(app_id=UUID("..."))
            )

            # With overrides - custom metadata takes precedence
            installed_app = await app_service.import_app(
                ImportAppRequest(
                    app_id=UUID("..."),
                    name="my-imported-app",
                    verbose_name="My Imported App",
                    description_short="Custom description"
                )
            )
            ```
        """
        # Query Apps API to get app details
        try:
            app_info = await self._apps_api_client.get_by_id(import_request.app_id)
        except AppsApiError:
            logger.exception("Failed to get app info from Apps API")
            raise AppServiceError(
                f"Unable to retrieve app with id {import_request.app_id} from Apps API"
            )

        # Fetch the actual inputs that were used when the app was installed
        # This provides accurate input for the template
        app_inputs = {}
        try:
            app_inputs = await self._apps_api_client.get_inputs(import_request.app_id)
            logger.info(
                f"Fetched inputs for app {import_request.app_id}: {list(app_inputs.keys())}"
            )
        except AppsApiError:
            logger.warning(
                f"Failed to fetch inputs for app {import_request.app_id}, "
                "will use empty dict for input"
            )

        # Extract template information from Apps API response
        template_name = app_info["template_name"]
        template_version = app_info["template_version"]
        app_name = app_info["name"]
        display_name = app_info["display_name"]

        # Fetch app endpoints (main URL and external URLs)
        url = None
        external_url_list: list[str] = []
        try:
            url, external_url_list = await self._apps_api_client.get_app_endpoints(
                import_request.app_id
            )
            logger.info(
                f"Fetched endpoints for app {import_request.app_id}: "
                f"url={url}, external_urls={len(external_url_list)}"
            )
        except AppsApiError:
            logger.warning(
                f"Failed to fetch endpoints for app {import_request.app_id}, "
                "will use null url and empty external_url_list"
            )

        # Create/update template using helper method
        # NOTE: We ignore import_request.name for app imports because the template
        # should always be identified by the template_name from Apps API, not a custom name.
        # The 'name' parameter is only meaningful for template imports (ImportTemplateRequest).
        template = await self._fetch_and_create_template(
            template_name=template_name,
            template_version=template_version,
            name=import_request.name,
            verbose_name=import_request.verbose_name,
            description_short=import_request.description_short,
            description_long=import_request.description_long,
            logo=import_request.logo,
            documentation_urls=import_request.documentation_urls,
            external_urls=import_request.external_urls,
            tags=import_request.tags,
            is_internal=import_request.is_internal or url is None,
            is_shared=True,  # Imported installed apps are always shared
            fallback_verbose_name=display_name,  # Use display_name as fallback
            input=app_inputs,  # Use actual inputs from the running app
        )

        # Link the app installation
        async with self._db() as db:
            async with db.begin():
                installed_app = await insert_app(
                    db=db,
                    app_id=import_request.app_id,
                    app_name=app_name,
                    launchpad_app_name=template.name,
                    is_internal=import_request.is_internal or url is None,
                    is_shared=True,  # Imported installed apps are always shared
                    user_id=None,
                    url=url,
                    template_name=template.name,  # Reference to AppTemplate
                    external_url_list=external_url_list,
                )

        await self._add_app_to_buffer(installed_app)
        return installed_app

    async def _fetch_and_create_template(
        self,
        template_name: str,
        template_version: str,
        name: str | None = None,
        verbose_name: str | None = None,
        description_short: str | None = None,
        description_long: str | None = None,
        logo: str | None = None,
        documentation_urls: list[dict[str, str]] | None = None,
        external_urls: list[dict[str, str]] | None = None,
        tags: list[str] | None = None,
        is_internal: bool = False,
        is_shared: bool = True,
        fallback_verbose_name: str | None = None,
        input: dict[str, Any] | None = None,
    ) -> AppTemplate:
        """
        Fetch template metadata from Apps API and create/update AppTemplate.

        This helper method:
        1. Fetches template metadata from Apps API
        2. Applies priority: user override > fallback > template metadata > defaults
        3. Creates/updates AppTemplate record

        Args:
            template_name: Apps API template name
            template_version: Apps API template version
            name: Custom name for the template (defaults to template_name)
            verbose_name: User-friendly display name
            description_short: Short description
            description_long: Long description
            logo: URL to logo
            documentation_urls: Documentation URLs
            external_urls: External URLs
            tags: Tags for categorization
            is_internal: Whether template is internal
            is_shared: Whether apps from this template can be shared
            fallback_verbose_name: Fallback for verbose_name (used by import_app for display_name)
            input: Default inputs to merge when installing

        Returns:
            The created/updated AppTemplate record

        Raises:
            AppServiceError: If template cannot be fetched from Apps API
        """
        # Fetch template details from Apps API
        template_info = None
        try:
            template_info = await self._apps_api_client.get_template(
                template_name, template_version
            )
        except AppsApiError:
            logger.warning(
                f"Failed to fetch template {template_name}:{template_version}, "
                "will use provided metadata only"
            )

        # Extract metadata from template
        if template_info:
            template_title = template_info.get("title", "")
            template_desc_short = template_info.get("short_description", "")
            template_desc_long = template_info.get("description", "")
            template_logo = template_info.get("logo", "")
            template_tags = template_info.get("tags", [])
            template_doc_urls = template_info.get("documentation_urls", [])
            template_ext_urls = template_info.get("external_urls", [])
        else:
            template_title = ""
            template_desc_short = ""
            template_desc_long = ""
            template_logo = ""
            template_tags = []
            template_doc_urls = []
            template_ext_urls = []

        # Apply priority logic: user override > fallback > template metadata > defaults
        resolved_name = name or template_name
        resolved_verbose_name = (
            verbose_name or fallback_verbose_name or template_title or resolved_name
        )
        resolved_description_short = description_short or template_desc_short
        resolved_description_long = description_long or template_desc_long
        resolved_logo = logo or template_logo
        resolved_documentation_urls = documentation_urls or template_doc_urls
        resolved_external_urls = external_urls or template_ext_urls
        resolved_tags = tags or template_tags

        # Create or update the template

        async with self._db() as db:
            async with db.begin():
                template = await insert_template(
                    db=db,
                    name=resolved_name,
                    template_name=template_name,
                    template_version=template_version,
                    verbose_name=resolved_verbose_name,
                    description_short=resolved_description_short,
                    description_long=resolved_description_long,
                    logo=resolved_logo,
                    documentation_urls=resolved_documentation_urls,
                    external_urls=resolved_external_urls,
                    tags=resolved_tags,
                    is_internal=is_internal,
                    is_shared=is_shared,
                    handler_class=None,
                    input=input,
                )

        return template

    async def create_or_update_template(
        self,
        name: str,
        template_name: str,
        template_version: str,
        verbose_name: str,
        description_short: str | None = None,
        description_long: str | None = None,
        logo: str | None = None,
        documentation_urls: list[dict[str, str]] | None = None,
        external_urls: list[dict[str, str]] | None = None,
        tags: list[str] | None = None,
        is_internal: bool = False,
        is_shared: bool = True,
        handler_class: str | None = None,
        input: dict[str, Any] | None = None,
    ) -> AppTemplate:
        """
        Create or update an AppTemplate record.

        This method encapsulates template creation logic that was previously
        done directly in the API layer.

        Args:
            name: Unique name for the template (used as identifier)
            template_name: Apps API template name
            template_version: Apps API template version
            verbose_name: User-friendly display name
            description_short: Short description
            description_long: Long description
            logo: URL to logo
            documentation_urls: Documentation URLs
            external_urls: External URLs
            tags: Tags for categorization
            is_internal: Whether template is internal
            is_shared: Whether apps from this template can be shared
            handler_class: Optional handler class for custom behavior
            input: Default inputs to merge when installing

        Returns:
            The created/updated AppTemplate record

        Raises:
            AppServiceError: If there's an error storing the template

        Example:
            ```python
            template = await app_service.create_or_update_template(
                name="my-app",
                template_name="my-template",
                template_version="1.0.0",
                verbose_name="My App",
                description_short="A custom application",
                input={"preset": {"name": "cpu-small"}}
            )
            ```
        """
        async with self._db() as db:
            async with db.begin():
                return await insert_template(
                    db=db,
                    name=name,
                    template_name=template_name,
                    template_version=template_version,
                    verbose_name=verbose_name,
                    description_short=description_short or "",
                    description_long=description_long or "",
                    logo=logo or "",
                    documentation_urls=documentation_urls or [],
                    external_urls=external_urls or [],
                    tags=tags or [],
                    is_internal=is_internal,
                    is_shared=is_shared,
                    handler_class=handler_class,
                    input=input,
                )

    async def import_template(
        self,
        import_request: ImportTemplateRequest,
    ) -> AppTemplate:
        """
        Import a template from Apps API and add it to the template pool.

        This method:
        1. Fetches the template metadata from Apps API
        2. Creates/updates an AppTemplate record
        3. Does NOT create an InstalledApp (just makes the template available)

        Args:
            import_request: Import request containing template info and optional metadata overrides

        Returns:
            The AppTemplate record

        Raises:
            AppsApiError: If the template cannot be found in Apps API
            AppServiceError: If there's an error storing the template

        Example:
            ```python
            # Import template with default settings
            template = await app_service.import_template(
                ImportTemplateRequest(
                    template_name="my-template",
                    template_version="1.0.0"
                )
            )

            # Import with custom metadata and shared setting
            template = await app_service.import_template(
                ImportTemplateRequest(
                    template_name="my-template",
                    template_version="1.0.0",
                    is_shared=False,  # Not a shared app
                    verbose_name="My Custom Template"
                )
            )
            ```
        """
        return await self._fetch_and_create_template(
            template_name=import_request.template_name,
            template_version=import_request.template_version,
            name=import_request.name,
            verbose_name=import_request.verbose_name,
            description_short=import_request.description_short,
            description_long=import_request.description_long,
            logo=import_request.logo,
            documentation_urls=import_request.documentation_urls,
            external_urls=import_request.external_urls,
            tags=import_request.tags,
            is_internal=import_request.is_internal,
            is_shared=import_request.is_shared,
            input=import_request.input,
        )

    async def delete(self, app_id: UUID) -> None:
        await self._apps_api_client.delete_app(app_id)
        async with self._db() as db:
            async with db.begin():
                await delete_app(db, app_id)

    async def delete_template_by_id(self, template_id: UUID) -> None:
        """
        Delete a template by its ID.

        This method:
        1. Finds the template by ID
        2. Gets all app instances that use this template
        3. Uninstalls each app instance via Apps API
        4. Deletes the template from the database

        Args:
            template_id: The UUID of the template to delete

        Raises:
            AppServiceError: If the template cannot be deleted
            NotFound: If the template doesn't exist
        """
        # Get the template to find its name
        async with self._db() as db:
            template = await select_template(db, id=template_id)

        if not template:
            raise NotFound(f"Template with id {template_id} not found")

        logger.info(
            f"Deleting template {template.name} (id={template_id}) "
            f"and all its instances"
        )

        # Get all app instances that use this template
        async with self._db() as db:
            installed_apps = await list_apps(db, template_name=template.name)

        logger.info(
            f"Found {len(installed_apps)} app instances to uninstall "
            f"for template {template.name}"
        )

        # Uninstall each app instance via Apps API and delete from DB
        for app in installed_apps:
            logger.info(
                f"Uninstalling app instance {app.app_id} "
                f"(launchpad_app_name={app.launchpad_app_name})"
            )
            try:
                await self._apps_api_client.delete_app(app.app_id)
            except AppsApiError as e:
                logger.warning(
                    f"Failed to uninstall app {app.app_id} from Apps API: {e}. "
                    "Continuing with deletion from database."
                )

            # Delete from database
            async with self._db() as db:
                async with db.begin():
                    await delete_app(db, app.app_id)

        # Finally, delete the template
        async with self._db() as db:
            async with db.begin():
                await delete_template(db, template_id)

        logger.info(f"Successfully deleted template {template.name} and all instances")

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

        handler_class = HANDLER_CLASSES[launchpad_app_name]
        app_context_class = cast(Any, APPS_CONTEXT[handler_class.__name__])
        app_context = await app_context_class.from_request(request=request)
        return app_class(context=app_context)

    async def list_app_pool(
        self,
        is_internal: bool = False,
    ) -> list[LaunchpadAppRead]:
        """
        Get the pool of available app templates.

        This method fetches templates from the database and converts them
        to LaunchpadAppRead format for API responses.

        Args:
            is_internal: Whether to include internal templates (default: False)

        Returns:
            List of LaunchpadAppRead objects representing available templates

        Example:
            ```python
            # Get non-internal templates (user-facing app pool)
            apps = await app_service.list_app_pool(is_internal=False)

            # Get all templates including internal ones
            all_apps = await app_service.list_app_pool(is_internal=True)
            ```
        """
        async with self._db() as db:
            templates = await list_templates(db, is_internal=is_internal)

        logger.info(f"Retrieved {len(templates)} templates (is_internal={is_internal})")

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

        return app_reads

    async def list_installed_apps(
        self,
        user_id: str | None = None,
    ) -> list[InstalledApp]:
        logger.info(f"Listing installed apps for user_id={user_id}")
        async with self._db() as db:
            apps = list(await list_apps(db, user_id=user_id))
            logger.info(f"Found {len(apps)} installed apps")
            for app in apps:
                logger.info(
                    f"  - {app.launchpad_app_name} (id={app.id}, "
                    f"user_id={app.user_id} "
                    f"is_internal={app.is_internal}, is_shared={app.is_shared})"
                )
            return apps

    async def list_unimported_instances(
        self,
        page: int = 1,
        size: int = 50,
    ) -> dict[str, Any]:
        """
        List app instances that exist in Apps API but haven't been imported into Launchpad.

        This method:
        1. Fetches all app instances from Apps API
        2. Gets list of imported app_ids from database
        3. Filters out instances that are already imported
        4. Filters to only include instances in healthy status

        Args:
            page: Page number (default: 1)
            size: Page size (default: 50, max: 100)

        Returns:
            Dict with paginated list of unimported healthy instances, including:
            - items: List of healthy app instances not yet imported
            - total: Total count of unimported healthy instances
            - page: Current page number
            - size: Page size
            - pages: Total number of pages

        Example:
            ```python
            result = await app_service.list_unimported_instances(page=1, size=50)
            for instance in result['items']:
                print(f"Unimported: {instance['name']} ({instance['id']})")
            ```
        """
        logger.info(f"Fetching unimported healthy instances (page={page}, size={size})")

        # Fetch only healthy instances from Apps API using states filter
        try:
            apps_api_response = await self._apps_api_client.list_instances(
                page=page, size=size, states=["healthy"]
            )
        except AppsApiError as e:
            logger.error(f"Failed to fetch instances from Apps API: {e}")
            raise AppServiceError("Unable to fetch instances from Apps API") from e

        healthy_instances = apps_api_response.get("items", [])
        logger.info(f"Fetched {len(healthy_instances)} healthy instances from Apps API")

        # Get all imported app_ids from database
        async with self._db() as db:
            imported_apps = await list_apps(db)

        imported_app_ids = {str(app.app_id) for app in imported_apps}
        logger.info(f"Found {len(imported_app_ids)} imported apps in database")

        # Filter out imported instances and launchpad templates
        # (filtering for healthy is now done by Apps API)
        unimported_instances = [
            instance
            for instance in healthy_instances
            if instance.get("id") not in imported_app_ids
            and instance.get("template_name") != "launchpad"
        ]

        logger.info(f"Found {len(unimported_instances)} unimported healthy instances")

        # Return paginated result matching the Apps API response structure
        return {
            "items": unimported_instances,
            "total": len(unimported_instances),
            "page": page,
            "size": size,
            "pages": (len(unimported_instances) + size - 1) // size,
        }


async def dep_app_service(request: Request) -> AppService:
    app: "Launchpad" = request.app
    return app.app_service


DepAppService = Annotated[AppService, Depends(dep_app_service)]
