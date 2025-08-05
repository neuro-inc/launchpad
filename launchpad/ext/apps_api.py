import typing
from typing import Any
from uuid import UUID

from aiohttp import ClientSession, ClientResponseError


class AppsApiError(Exception):
    pass


class NotFound(AppsApiError):
    pass


class ServerError(AppsApiError):
    pass


class AppsApiClient:
    def __init__(
        self,
        http: ClientSession,
        base_url: str,
        token: str,
        cluster: str,
        org_name: str,
        project_name: str,
    ):
        self._http = http
        self._base_url = base_url
        self._token = token
        self._cluster = cluster
        self._org_name = org_name
        self._project_name = project_name

    @property
    def v1_url(self) -> str:
        return f"{self._base_url}/v1/cluster/{self._cluster}/org/{self._org_name}/project/{self._project_name}"

    @property
    def v2_url(self) -> str:
        return f"{self._base_url}/v2"

    @property
    def default_params(self) -> dict[str, str]:
        return {
            "cluster": self._cluster,
            "org": self._org_name,
            "project": self._project_name,
        }

    @property
    def default_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def get_by_id(self, app_id: UUID) -> dict[str, Any]:
        return await self._request(
            method="GET",
            url=f"{self.v2_url}/instances/{app_id}",
        )

    async def get_outputs(self, app_id: UUID) -> dict[str, Any]:
        return await self._request(
            method="GET", url=f"{self.v1_url}/instances/{app_id}/output"
        )

    async def install_app(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.v1_url}/instances"
        return await self._request(
            method="POST",
            url=url,
            json=payload,
        )

    async def delete_app(self, app_id: UUID) -> None:
        await self._request(
            method="DELETE",
            url=f"{self.v1_url}/instances/{app_id}",
        )

    async def _request(
        self, method: str, url: str, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers.update(self.default_headers)
        try:
            response = await self._http.request(  # type: ignore[call-arg]
                method,
                url,
                *args,
                headers=headers,
                verify_ssl=False,  # todo: check why requests are failing with SSL error
                **kwargs,
            )
        except TimeoutError as e:
            raise AppsApiError() from e

        try:
            response.raise_for_status()
        except ClientResponseError as e:
            match e.status:
                case 404:
                    raise NotFound() from e
                case 500:
                    raise ServerError() from e
                case _:
                    raise AppsApiError() from e

        try:
            response = await response.json()
            return typing.cast(dict[str, Any], response)
        except ValueError as e:
            raise AppsApiError() from e
