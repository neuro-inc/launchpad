from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, Self
from typing import TypeVar

from starlette.requests import Request

from launchpad.app import Launchpad


@dataclass
class BaseContext:
    """
    A base context, that will be passed to each app
    """

    @classmethod
    async def from_app(cls, app: Launchpad) -> Self:
        raise NotImplementedError()

    @classmethod
    async def from_request(cls, request: Request) -> Self:
        raise NotImplementedError()


T_Context = TypeVar("T_Context", bound=BaseContext)


class App(ABC, Generic[T_Context]):
    name: str
    template_name: str
    template_version: str
    is_internal: bool
    is_shared: bool
    verbose_name: str
    description_short: str
    description_long: str
    logo: str
    documentation_urls: list[dict[str, str]]
    external_urls: list[dict[str, str]]
    tags: list[str]

    def __init__(
        self,
        context: T_Context,
    ):
        self._context = context

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__

    async def to_apps_api_payload(
        self,
    ) -> dict[str, Any]:
        return {
            "template_name": self.template_name,
            "template_version": self.template_version,
            "input": await self._generate_inputs(),
        }

    @abstractmethod
    async def _generate_inputs(self) -> dict[str, Any]:
        raise NotImplementedError()


class GenericApp(App[BaseContext]):
    """
    A generic app class that can be instantiated with any template and inputs.
    This allows for dynamic app installation without defining specific app classes.
    """

    def __init__(
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
    ):
        """
        Initialize a generic app.

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
        """
        # Create a minimal context since we don't need complex context for generic apps
        context = BaseContext()
        super().__init__(context)

        self.name = name or template_name
        self.template_name = template_name
        self.template_version = template_version
        self._inputs = inputs
        self.is_internal = is_internal
        self.is_shared = is_shared
        self.verbose_name = verbose_name or template_name
        self.description_short = description_short
        self.description_long = description_long
        self.logo = logo
        self.documentation_urls = documentation_urls or []
        self.external_urls = external_urls or []
        self.tags = tags or []

    async def _generate_inputs(self) -> dict[str, Any]:
        return self._inputs
