import logging
from typing import Any
from uuid import UUID

from aiohttp import ClientResponseError, ClientSession
from apolo_sdk import Client as ApoloClient


logger = logging.getLogger(__name__)


class LaunchpadApiError(Exception):
    pass


def _service_api_to_url(service_api: dict[str, Any]) -> str | None:
    url = service_api.get("external_url") or service_api.get("internal_url")
    if not isinstance(url, dict):
        return None

    protocol = url.get("protocol")
    host = url.get("host")
    base_path = url.get("base_path") or "/"
    if not isinstance(protocol, str) or not isinstance(host, str):
        return None

    normalized_base_path = base_path.rstrip("/") if base_path != "/" else ""
    return f"{protocol}://{host}{normalized_base_path}"


def _extract_admin_api_url(outputs: dict[str, Any]) -> str | None:
    admin_api = outputs.get("admin_api")
    if not isinstance(admin_api, dict):
        return None

    api_url = admin_api.get("api_url")
    if not isinstance(api_url, dict):
        return None

    return _service_api_to_url(api_url)


def _extract_admin_username(outputs: dict[str, Any]) -> str | None:
    admin_user = outputs.get("admin_user")
    if not isinstance(admin_user, dict):
        return None

    username = admin_user.get("username")
    return username if isinstance(username, str) and username else None


def _extract_admin_password_secret_key(outputs: dict[str, Any]) -> str | None:
    admin_user = outputs.get("admin_user")
    if not isinstance(admin_user, dict):
        return None

    password = admin_user.get("password")
    if not isinstance(password, dict):
        return None

    key = password.get("key")
    return key if isinstance(key, str) and key else None


class LaunchpadAdminApi:
    def __init__(
        self,
        *,
        http: ClientSession,
        base_url: str,
        username: str,
        password: str,
    ):
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._access_token: str | None = None

    @classmethod
    async def from_outputs(
        cls,
        *,
        http: ClientSession,
        apolo_client: ApoloClient,
        cluster_name: str,
        org_name: str,
        project_name: str,
        outputs: dict[str, Any],
    ) -> "LaunchpadAdminApi":
        base_url = _extract_admin_api_url(outputs)
        if base_url is None:
            raise LaunchpadApiError("admin API URL is missing in outputs")

        username = _extract_admin_username(outputs)
        if username is None:
            raise LaunchpadApiError("admin username is missing in outputs")

        password_secret_key = _extract_admin_password_secret_key(outputs)
        if password_secret_key is None:
            raise LaunchpadApiError(
                "admin password secret reference is missing in outputs"
            )

        try:
            password = (
                await apolo_client.secrets.get(
                    password_secret_key,
                    cluster_name=cluster_name,
                    org_name=org_name,
                    project_name=project_name,
                )
            ).decode()
        except Exception as e:
            raise LaunchpadApiError(
                "admin password secret could not be resolved"
            ) from e

        return cls(
            http=http,
            base_url=base_url,
            username=username,
            password=password,
        )

    async def _login(self) -> str:
        response = await self._http.post(
            f"{self._base_url}/auth/token",
            json={"username": self._username, "password": self._password},
            ssl=False,
        )
        raw_response = await response.text(errors="ignore")
        try:
            response.raise_for_status()
        except ClientResponseError as e:
            logger.warning(
                "Launchpad admin auth failed with status %s: %s",
                e.status,
                raw_response,
            )
            raise LaunchpadApiError("failed to authenticate to Launchpad") from e

        payload = await response.json()
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise LaunchpadApiError(
                "Launchpad token response did not include access_token"
            )

        return access_token

    async def _get_access_token(self) -> str:
        if self._access_token is None:
            self._access_token = await self._login()
        return self._access_token

    async def _authorized_delete(self, path: str, **kwargs: Any) -> bool:
        access_token = await self._get_access_token()
        response = await self._http.delete(
            f"{self._base_url}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            ssl=False,
            **kwargs,
        )
        if response.status == 404:
            logger.info("Launchpad resource %s is not present, skipping delete", path)
            return False

        raw_response = await response.text(errors="ignore")
        try:
            response.raise_for_status()
        except ClientResponseError as e:
            logger.warning(
                "Launchpad admin DELETE %s failed with status %s: %s",
                path,
                e.status,
                raw_response,
            )
            raise LaunchpadApiError("Launchpad admin DELETE request failed") from e
        return True

    async def delete_app_template_by_app_id(
        self,
        app_id: UUID,
        *,
        uninstall: bool,
    ) -> bool:
        return await self._authorized_delete(
            f"/api/v1/apps/templates/by-instance/{app_id}",
            params={"uninstall": str(uninstall).lower()},
        )

    async def delete_app(self, app_id: UUID, *, uninstall: bool) -> bool:
        return await self._authorized_delete(
            f"/api/v1/apps/instances/{app_id}",
            params={"uninstall": str(uninstall).lower()},
        )
