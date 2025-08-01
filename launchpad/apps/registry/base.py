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
    documentation_urls: list[str]
    external_urls: list[str]
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
