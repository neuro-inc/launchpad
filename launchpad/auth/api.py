import logging
from typing import Any, Mapping
from urllib.parse import urlparse, urlsplit, urlunsplit

import aiohttp
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import (
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from launchpad.apps.service import DepAppService
from launchpad.auth import (
    AUTH_REDIRECT_HEADERS,
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_ROLES,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_FORWARDED_HOST,
    HEADER_X_FORWARDED_URI,
)
from launchpad.auth.dependencies import (
    _extract_bearer_token,
    authorize_app_email,
    decode_app_token,
    decode_token_from_request,
    get_raw_token_from_request,
    resolve_app_for_authorization,
    token_from_string,
)
from launchpad.auth.oauth import DepOauth, OauthError
from launchpad.auth.static_hostname import DepStaticHostnameAuth
from launchpad.auth.static_hostname_api import (
    begin_static_hostname_login,
    handle_static_hostname_handoff,
)
from launchpad.errors import Forbidden, Unauthorized
from launchpad.hostnames import canonical_authority


_token_from_request = get_raw_token_from_request

logger = logging.getLogger(__name__)

auth_router = APIRouter()


def _normalize_prefix(prefix: str) -> str:
    normalized = prefix.strip()
    if not normalized:
        return ""
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/" and normalized.endswith("/"):
        normalized = normalized.rstrip("/")
    return normalized


def _is_auth_bypass_path(request_path: str, prefixes: list[str]) -> bool:
    if not request_path:
        return False
    for raw_prefix in prefixes:
        prefix = _normalize_prefix(raw_prefix)
        if not prefix:
            continue
        if prefix == "/":
            return True
        if request_path == prefix or request_path.startswith(f"{prefix}/"):
            return True
    return False


class TokenRequest(BaseModel):
    username: str
    password: str
    scope: str = "openid profile email offline_access"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None


def _validate_origin(request: Request) -> None:
    """Validate Origin/Referer headers against configured public URL."""
    web_domain = request.app.config.apolo.web_app_domain
    # web_app_domain is a bare hostname — urlparse needs a scheme to extract .hostname
    expected_host = urlparse(web_domain).hostname or web_domain

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    origin_valid = origin and urlparse(origin).hostname == expected_host
    referer_valid = referer and urlparse(referer).hostname == expected_host

    if not (origin_valid or referer_valid):
        logger.warning(
            f"CSRF check failed: origin={origin}, referer={referer}, expected={expected_host}"
        )
        raise Forbidden("Invalid request origin")


async def _validate_token_audience(
    decoded: Mapping[str, Any],
    keycloak_config: Any,
) -> None:
    """Validate token audience/azp matches expected client."""
    expected_client = keycloak_config.client_id
    aud = decoded.get("aud", [])

    if isinstance(aud, str):
        aud = [aud]
    elif not isinstance(aud, list):
        aud = []

    azp = decoded.get("azp")

    if not (azp == expected_client or expected_client in aud):
        logger.warning(
            f"Audience mismatch: expected={expected_client}, aud={aud}, azp={azp}"
        )
        raise Unauthorized("Invalid token audience")


@auth_router.post("/token", response_model=TokenResponse)
async def get_token(
    request: Request,
    token_request: TokenRequest,
) -> JSONResponse:
    """
    Obtain an access token using username and password.
    This proxies the request to Keycloak's token endpoint.
    """
    keycloak_config = request.app.config.keycloak
    token_url = f"{keycloak_config.url}/realms/{keycloak_config.realm}/protocol/openid-connect/token"

    data = {
        "grant_type": "password",
        "client_id": keycloak_config.client_id,
        "username": token_request.username,
        "password": token_request.password,
        "scope": token_request.scope,
    }

    # Determine SSL verification setting (default True).
    ssl_verify = keycloak_config.ssl_verify

    try:
        async with request.app.http.post(
            token_url, data=data, ssl=ssl_verify
        ) as response:
            # Handle authentication errors (wrong credentials)
            if response.status == 401:
                error_data = await response.json()
                error_description = error_data.get(
                    "error_description", "Invalid credentials"
                )
                logger.warning(
                    f"Authentication failed for user '{token_request.username}': {error_description}"
                )
                raise Unauthorized("Invalid username or password")

            # Handle client errors (bad request, forbidden, etc.)
            elif 400 <= response.status < 500:
                error_data = await response.json()
                error_description = error_data.get("error_description", "Client error")
                logger.warning(
                    f"Client error during token request (status {response.status}): {error_description}"
                )
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Authentication error: {error_description}",
                )

            # Handle server errors (Keycloak issues)
            elif response.status >= 500:
                error_text = await response.text()
                logger.error(
                    f"Keycloak server error (status {response.status}): {error_text}"
                )
                raise HTTPException(
                    status_code=503,
                    detail="Authentication service is temporarily unavailable. Please try again later.",
                )

            # Success case
            response.raise_for_status()
            token_data = await response.json()
            return JSONResponse(content=token_data)

    except (Unauthorized, HTTPException):
        # Re-raise our custom exceptions
        raise
    except aiohttp.ClientConnectionError as e:
        logger.error(f"Failed to connect to Keycloak at {token_url}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to authentication service. Please try again later.",
        )
    except aiohttp.ClientError as e:
        logger.error(f"HTTP client error during token request: {e}")
        raise HTTPException(
            status_code=502, detail="Error communicating with authentication service."
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error during token request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during authentication.",
        )


@auth_router.get("/authorize", status_code=200)
async def view_post_authorize(
    request: Request,
    app_service: DepAppService,
    oauth: DepOauth,
    static_hostname_auth: DepStaticHostnameAuth,
) -> Response:
    forwarded_hostname = request.headers[HEADER_X_FORWARDED_HOST]
    try:
        hostname = canonical_authority(forwarded_hostname)
    except ValueError:
        raise Forbidden("Invalid forwarded hostname") from None
    app_url = f"https://{hostname}"
    is_cross_domain = not oauth.covers_hostname(hostname)
    installed_app = await resolve_app_for_authorization(app_service, hostname)
    if installed_app is None:
        logger.info(f"Unable to find installed app by url: {app_url}")
        raise Forbidden()

    if hostname != forwarded_hostname:
        forwarded_uri = urlsplit(request.headers.get(HEADER_X_FORWARDED_URI, ""))
        return RedirectResponse(
            urlunsplit(
                ("https", hostname, forwarded_uri.path or "/", forwarded_uri.query, "")
            ),
            headers=AUTH_REDIRECT_HEADERS,
        )

    handoff_response = await handle_static_hostname_handoff(
        request,
        installed_app.app_id,
        static_hostname_auth,
        hostname=hostname,
        is_cross_domain=is_cross_domain,
    )
    if handoff_response is not None:
        return handoff_response

    request_path = request.headers.get(HEADER_X_FORWARDED_URI, "")
    auth_bypass_path_prefixes = request.app.config.auth_bypass_path_prefixes or []
    if _is_auth_bypass_path(request_path, auth_bypass_path_prefixes):
        logger.debug(
            "Bypassing auth redirect for path '%s' by prefixes: %s",
            request_path,
            auth_bypass_path_prefixes,
        )
        return PlainTextResponse("OK", status_code=200)

    # make internal apps accessible for apps that only expose an api, not a web page
    # if installed_app.is_internal:
    #     logger.info("access to an internal app is forbidden")
    #     raise Forbidden()

    try:
        decoded_token = await decode_app_token(
            request,
            installed_app.app_id,
            oauth,
            static_hostname_auth,
            hostname=hostname,
            is_cross_domain=is_cross_domain,
        )
    except Unauthorized:
        logger.info(
            "no access token present or unable to decode. redirecting to keycloak"
        )
        if not is_cross_domain:
            return oauth.redirect(original_redirect_uri=app_url)
        return await begin_static_hostname_login(
            hostname, installed_app.app_id, oauth, static_hostname_auth
        )

    logger.debug(f"Decoded token keys: {list(decoded_token.keys())}")
    logger.debug(f"Token realm_access: {decoded_token.get('realm_access')}")
    logger.debug(f"Token groups: {decoded_token.get('groups')}")

    email = authorize_app_email(installed_app, decoded_token)

    # extract username from token
    username = str(decoded_token.get("preferred_username", email))

    # groups and realm roles are forwarded separately to downstream apps.
    groups = decoded_token.get("groups", [])
    realm_roles = decoded_token.get("realm_access", {}).get("roles", [])
    groups_str = ",".join(groups) if groups else ""
    roles_str = ",".join(realm_roles) if realm_roles else ""

    logger.debug(
        f"Authorizing user - Email: {email}, Username: {username}, Groups: {groups_str}, Roles: {roles_str}"
    )

    # check permissions for individual apps
    response_headers: dict[str, str] = {
        # pass headers to a downstream app via traefik auth middleware
        HEADER_X_AUTH_REQUEST_EMAIL: email,
        HEADER_X_AUTH_REQUEST_USERNAME: username,
        HEADER_X_AUTH_REQUEST_GROUPS: groups_str,
        HEADER_X_AUTH_REQUEST_ROLES: roles_str,
    }

    logger.debug(f"Returning auth headers: {response_headers}")

    return PlainTextResponse(
        "OK",
        status_code=200,
        headers=response_headers,
    )


@auth_router.api_route("/callback", methods=["GET", "POST"], status_code=200)
async def callback(request: Request, oauth: DepOauth) -> Response:
    """
    GET: Standard OAuth callback from Keycloak (after PKCE redirect).
        - Keycloak redirects here with ?code=...&state=...
        - oauth.callback() exchanges code for token, validates state, sets cookie

    POST: Set cookie from existing Bearer token (called by frontend after PKCE login).
        - Frontend already has token from NextAuth PKCE flow
        - Validates token, checks audience, sets secure cookie for Traefik ForwardAuth
    """

    # --- GET: Standard OAuth callback ---
    if request.method == "GET":
        try:
            response: Response = await oauth.callback(request)
            response.headers.update(AUTH_REDIRECT_HEADERS)
            return response
        except OauthError as e:
            raise Forbidden(str(e))

    # --- POST: Set cookie from Bearer token ---
    if request.method == "POST":
        # CSRF protection
        _validate_origin(request)

        # Extract and validate token (require Authorization header)
        access_token = _extract_bearer_token(request.headers.get("Authorization"))
        if not access_token:
            raise Unauthorized("Missing or invalid Authorization header")

        try:
            decoded = await token_from_string(
                http=request.app.http,
                keycloak_config=request.app.config.keycloak,
                access_token=access_token,
            )
        except Unauthorized:
            raise
        except Exception as e:
            logger.error(f"Token validation error in /callback POST: {e}")
            raise Unauthorized("Invalid or expired token")

        # Audience check
        await _validate_token_audience(decoded, request.app.config.keycloak)

        # Set secure cookie
        response = Response("OK", status_code=200)

        # Ensure oauth.set_auth_cookie() sets Secure, HttpOnly, SameSite=Lax
        oauth.set_auth_cookie(response, access_token)
        return response

    raise HTTPException(status_code=405, detail="Method not allowed")


@auth_router.post("/logout", status_code=200)
async def logout(
    request: Request, oauth: DepOauth, static_hostname_auth: DepStaticHostnameAuth
) -> Response:
    try:
        decoded = await decode_token_from_request(request, oauth)
    except Unauthorized:
        pass
    else:
        email = decoded.get("email")
        if isinstance(email, str) and email:
            await static_hostname_auth.revoke_user(email)
    response = Response(status_code=200)
    oauth.logout(response)
    return response
