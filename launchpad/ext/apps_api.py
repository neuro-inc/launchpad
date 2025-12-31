import logging
import typing
from typing import Any
from uuid import UUID

from aiohttp import ClientResponseError, ClientSession


logger = logging.getLogger(__name__)


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

    async def get_template(
        self, template_name: str, template_version: str
    ) -> dict[str, Any]:
        """Get template details by name and version"""
        return await self._request(
            method="GET",
            url=f"{self.v2_url}/templates/{template_name}/{template_version}",
        )

    async def get_outputs(self, app_id: UUID) -> dict[str, Any]:
        return await self._request(
            method="GET", url=f"{self.v1_url}/instances/{app_id}/output"
        )

    async def get_inputs(self, app_id: UUID) -> dict[str, Any]:
        """Get the input parameters that were used when installing the app"""
        return await self._request(
            method="GET", url=f"{self.v1_url}/instances/{app_id}/input"
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
            response = await self._http.request(
                method,
                url,
                *args,
                headers=headers,
                ssl=False,  # todo: check why requests are failing with SSL error
                **kwargs,
            )
        except TimeoutError as e:
            raise AppsApiError() from e

        raw_response = await response.text(errors="ignore")

        try:
            response.raise_for_status()
        except ClientResponseError as e:
            logger.error(f"Bad response: {raw_response}")
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
            logger.error(f"Bad response: {raw_response}")
            raise AppsApiError() from e

    async def update_outputs(
        self,
        app_id: UUID,
        outputs: dict[str, Any],
    ) -> None:
        await self._request(
            method="POST",
            url=f"{self.v1_url}/instances/{app_id}/output",
            json={"output": outputs},
        )

    async def list_instances(
        self,
        page: int = 1,
        size: int = 50,
        states: list[str] | None = None,
    ) -> dict[str, Any]:
        """List all app instances in the cluster/org/project

        Args:
            page: Page number
            size: Page size
            states: Optional list of app states to filter by (e.g., ["healthy"])
        """
        params: dict[str, Any] = {
            **self.default_params,
            "page": page,
            "size": size,
        }
        if states:
            params["states"] = states

        return await self._request(
            method="GET",
            url=f"{self.v2_url}/instances",
            params=params,
        )

    def _extract_service_api_urls(self, data: Any) -> list[str]:
        """Recursively search for ServiceAPI objects and extract their external URLs"""
        urls = []

        if isinstance(data, dict):
            # Check if this dict is a ServiceAPI object
            type_value = data.get("__type__")
            if isinstance(type_value, str) and type_value.startswith("ServiceAPI["):
                # Extract external_url from this ServiceAPI object
                external_url = data.get("external_url")
                if isinstance(external_url, dict):
                    protocol = external_url.get("protocol")
                    host = external_url.get("host")
                    base_path = external_url.get("base_path", "/")

                    if protocol and host:
                        # Normalize URL - don't include trailing slash for base path "/"
                        if base_path == "/":
                            full_url = f"{protocol}://{host}"
                        else:
                            # Remove trailing slash from base_path if present
                            base_path = base_path.rstrip("/")
                            full_url = f"{protocol}://{host}{base_path}"
                        urls.append(full_url)

            # Recursively search in all values
            for value in data.values():
                urls.extend(self._extract_service_api_urls(value))

        elif isinstance(data, list):
            # Recursively search in list items
            for item in data:
                urls.extend(self._extract_service_api_urls(item))

        return urls

    async def get_app_endpoints(self, app_id: UUID) -> tuple[str | None, list[str]]:
        """
        Get the main app URL and list of external endpoint URLs from app outputs.

        Args:
            app_id: The app instance ID

        Returns:
            Tuple of (main_url, external_urls_list)
            - main_url: The main app URL from outputs["app_url"]["external_url"], or None
            - external_urls_list: List of external endpoint URLs from ServiceAPI objects

        Raises:
            AppsApiError: If the request to get outputs fails
        """
        outputs = await self.get_outputs(app_id)

        # Extract main app URL
        main_url = None
        try:
            app_url_output = outputs.get("app_url")
            if app_url_output and isinstance(app_url_output, dict):
                external_url = app_url_output.get("external_url")
                if isinstance(external_url, dict):
                    protocol = external_url.get("protocol")
                    host = external_url.get("host")
                    base_path = external_url.get("base_path", "/")

                    if protocol and host:
                        # Normalize URL - don't include trailing slash for base path "/"
                        if base_path == "/":
                            main_url = f"{protocol}://{host}"
                        else:
                            # Remove trailing slash from base_path if present
                            base_path = base_path.rstrip("/")
                            main_url = f"{protocol}://{host}{base_path}"
        except (KeyError, TypeError):
            logger.debug(f"No main app_url found for app {app_id}")

        # Extract all ServiceAPI external URLs
        external_urls = self._extract_service_api_urls(outputs)

        return main_url, external_urls
