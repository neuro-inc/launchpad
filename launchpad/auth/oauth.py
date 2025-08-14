import base64
import hashlib
import logging
import os
import typing
from typing import Annotated, TYPE_CHECKING
from urllib.parse import urlencode

import backoff
from aiohttp import ClientSession, ClientConnectionError, ClientResponseError
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse

from launchpad.config import KeycloakConfig

if TYPE_CHECKING:
    from launchpad.app import Launchpad


logger = logging.getLogger(__name__)


COOKIE_TOKEN = "launchpad-token"
COOKIE_CODE_VERIFIER = "code_verifier"


class OauthError(Exception): ...


class Retry(Exception): ...


class Oauth:
    def __init__(
        self,
        http: ClientSession,
        keycloak_config: KeycloakConfig,
        cookie_domain: str,
        launchpad_domain: str,
        scope: list[str] | None = None,
    ):
        self._http = http
        self._url = keycloak_config.url
        self._realm = keycloak_config.realm
        self._client_id = keycloak_config.client_id
        self._cookie_domain = f".{cookie_domain}"
        self._launchpad_domain = launchpad_domain
        self._callback_url = f"https://{self._launchpad_domain}/auth/callback"
        self._keycloak_url = f"{self._url}/realms/{self._realm}/protocol/openid-connect"
        self._token_url = f"{self._keycloak_url}/token"
        self._scope = " ".join(
            scope or ["openid", "profile", "email", "offline_access"]
        )

    def redirect(
        self,
        original_redirect_uri: str,
    ) -> RedirectResponse:
        """Returns a redirect response, preserving an original url in a `state` param"""
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        state = base64.urlsafe_b64encode(original_redirect_uri.encode()).decode()

        auth_url = f"{self._keycloak_url}/auth?" + urlencode(
            {
                "client_id": self._client_id,
                "response_type": "code",
                "scope": self._scope,
                "redirect_uri": self._callback_url,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": state,
            }
        )

        response = RedirectResponse(url=auth_url)
        self._set_cookie(response, key=COOKIE_CODE_VERIFIER, value=code_verifier)
        return response

    def get_token_from_cookie(self, request: Request) -> str | None:
        return request.cookies.get(COOKIE_TOKEN)

    async def callback(self, request: Request) -> RedirectResponse:
        try:
            code = request.query_params["code"]
            state = request.query_params["state"]
            code_verifier = request.cookies["code_verifier"]
        except KeyError:
            raise OauthError("missing required params")

        original_url = base64.urlsafe_b64decode(state.encode()).decode()

        data = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "code": code,
            "redirect_uri": self._callback_url,
            "code_verifier": code_verifier,
        }
        access_token = await self._fetch_token(data)

        response = RedirectResponse(original_url)
        self._set_cookie(response, key=COOKIE_TOKEN, value=access_token)
        return response

    def logout(self, response: Response) -> None:
        """Cleanup of cookies on logout"""
        for cookie in (COOKIE_TOKEN, COOKIE_CODE_VERIFIER):
            response.delete_cookie(
                key=cookie, domain=self._cookie_domain, secure=True, httponly=True
            )

    @backoff.on_exception(
        wait_gen=backoff.expo,
        exception=(ClientConnectionError, Retry),
    )
    async def _fetch_token(self, data: dict[str, str]) -> str:
        async with self._http.post(  # type: ignore[call-arg]
            self._token_url, data=data, verify_ssl=False
        ) as response:
            try:
                response.raise_for_status()
            except ClientResponseError as e:
                if e.status >= 500:
                    raise Retry()
                logger.error("unable to fetch token")
                raise OauthError()
            try:
                token_data = await response.json()
                return typing.cast(str, token_data["access_token"])
            except (TypeError, ValueError, KeyError):
                logger.error("unable to extract access token")
                raise OauthError()

    def _set_cookie(
        self,
        response: Response,
        key: str,
        value: str,
    ) -> None:
        response.set_cookie(
            key=key,
            value=value,
            domain=self._cookie_domain,
            secure=True,
            httponly=True,
        )


def dep_oauth(request: Request) -> Oauth:
    app: "Launchpad" = request.app
    return app.oauth


DepOauth = Annotated[Oauth, Depends(dep_oauth)]
