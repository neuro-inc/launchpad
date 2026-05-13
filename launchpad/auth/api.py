import hashlib
import logging
import time
from typing import Any, Mapping
from urllib.parse import urlparse

import aiohttp
import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import (
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

from launchpad.apps.storage import select_app_by_any_url
from launchpad.auth import (
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_FORWARDED_HOST,
)
from launchpad.auth.dependencies import (
    _extract_bearer_token,
    decode_token_from_request,
    get_raw_token_from_request,
    token_from_string,
)


_token_from_request = get_raw_token_from_request
from launchpad.auth.oauth import DepOauth, OauthError
from launchpad.db.dependencies import Db
from launchpad.errors import Forbidden, Unauthorized


logger = logging.getLogger(__name__)

auth_router = APIRouter()


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


def _request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id")


def _correlation_id(request: Request) -> str | None:
    return request.headers.get("x-correlation-id") or request.headers.get(
        "x-amzn-trace-id"
    )


def _classify_launch_url(host: str) -> str:
    if host.startswith("localhost") or host.startswith("127.0.0.1"):
        return "local"
    if host.endswith(".internal"):
        return "internal"
    return "public"


def _safe_token_meta(raw_token: str | None) -> dict[str, Any]:
    if not raw_token:
        return {"token_present": False}
    meta: dict[str, Any] = {"token_present": True}
    try:
        payload = jwt.decode(raw_token, options={"verify_signature": False})
    except jwt.PyJWTError:
        meta["token_claims_parse"] = "failed"
        return meta
    exp = payload.get("exp")
    now = int(time.time())
    if isinstance(exp, int):
        meta["token_exp_unix"] = exp
        meta["token_ttl_s"] = max(exp - now, 0)
    if isinstance(payload.get("iss"), str):
        meta["token_issuer_present"] = True
    if payload.get("aud") is not None:
        meta["token_audience_present"] = True
    return meta


def _mask_subject(subject: str) -> str:
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:12]


def _validate_origin(request: Request) -> None:
    """Validate Origin/Referer headers against configured public URL."""
    expected_host = urlparse(request.app.config.apolo.web_app_domain).hostname

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    origin_valid = origin and urlparse(origin).hostname == expected_host
    referer_valid = referer and urlparse(referer).hostname == expected_host

    if not (origin_valid or referer_valid):
        origin_host = urlparse(origin).hostname if origin else None
        referer_host = urlparse(referer).hostname if referer else None
        logger.warning(
            "csrf_origin_validation_failed",
            extra={
                "event_name": "launchpad.auth.csrf.reject",
                "reason_code": "INVALID_ORIGIN_OR_REFERER",
                "origin_host": origin_host,
                "referer_host": referer_host,
                "expected_host": expected_host,
            },
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
                    "auth_token_password_grant_rejected",
                    extra={
                        "event_name": "launchpad.auth.password_grant.reject",
                        "reason_code": "INVALID_CREDENTIALS",
                        "subject_hash": _mask_subject(token_request.username),
                    },
                )
                raise Unauthorized("Invalid username or password")

            # Handle client errors (bad request, forbidden, etc.)
            elif 400 <= response.status < 500:
                error_data = await response.json()
                error_description = error_data.get("error_description", "Client error")
                logger.warning(
                    "auth_token_client_error",
                    extra={
                        "event_name": "launchpad.auth.password_grant.error",
                        "reason_code": "UPSTREAM_4XX",
                        "upstream_status": response.status,
                    },
                )
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Authentication error: {error_description}",
                )

            # Handle server errors (Keycloak issues)
            elif response.status >= 500:
                error_text = await response.text()
                logger.error(
                    "auth_token_keycloak_server_error",
                    extra={
                        "event_name": "launchpad.auth.password_grant.error",
                        "reason_code": "UPSTREAM_5XX",
                        "upstream_status": response.status,
                        "error_text_present": bool(error_text),
                    },
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
    db: Db,
    oauth: DepOauth,
) -> Response:
    forwarded_host = request.headers[HEADER_X_FORWARDED_HOST]
    app_url = f"https://{forwarded_host}"
    req_id = _request_id(request)
    corr_id = _correlation_id(request)
    logger.info(
        "launch_authorize_started",
        extra={
            "event_name": "launchpad.auth.launch.authorize.start",
            "reason_code": "START",
            "request_id": req_id,
            "correlation_id": corr_id,
            "target_host": forwarded_host,
            "launch_url_category": _classify_launch_url(forwarded_host),
        },
    )

    installed_app = await select_app_by_any_url(db=db, url=app_url)
    if installed_app is None:
        logger.info(
            "launch_authorize_app_not_found",
            extra={
                "event_name": "launchpad.auth.launch.authorize.reject",
                "reason_code": "APP_NOT_FOUND_BY_URL",
                "request_id": req_id,
                "correlation_id": corr_id,
                "target_host": forwarded_host,
            },
        )
        raise Forbidden()

    # make internal apps accessible for apps that only expose an api, not a web page
    # if installed_app.is_internal:
    #     logger.info("access to an internal app is forbidden")
    #     raise Forbidden()

    # Attempt to decode token (prefers cookie when oauth provided)
    raw_token = _token_from_request(request, oauth, allow_cookie=True)
    token_meta = _safe_token_meta(raw_token)
    logger.info(
        "launch_authorize_token_presence_checked",
        extra={
            "event_name": "launchpad.auth.launch.token.checked",
            "reason_code": "TOKEN_PRESENCE_CHECKED",
            "request_id": req_id,
            "correlation_id": corr_id,
            "app_name": installed_app.launchpad_app_name,
            "app_id": str(installed_app.app_id),
            **token_meta,
        },
    )
    try:
        decoded_token = await decode_token_from_request(request, oauth)
        await _validate_token_audience(decoded_token, request.app.config.keycloak)
    except Unauthorized:
        logger.info(
            "launch_authorize_redirect_to_idp",
            extra={
                "event_name": "launchpad.auth.launch.redirect",
                "reason_code": "TOKEN_MISSING_OR_INVALID",
                "request_id": req_id,
                "correlation_id": corr_id,
                "app_name": installed_app.launchpad_app_name,
                "app_id": str(installed_app.app_id),
                **token_meta,
            },
        )
        return oauth.redirect(original_redirect_uri=app_url)

    try:
        email = decoded_token["email"]
    except KeyError:
        logger.error(
            "launch_authorize_missing_email_claim",
            extra={
                "event_name": "launchpad.auth.launch.authorize.reject",
                "reason_code": "MISSING_EMAIL_CLAIM",
                "request_id": req_id,
                "correlation_id": corr_id,
                "app_name": installed_app.launchpad_app_name,
                "app_id": str(installed_app.app_id),
            },
        )
        raise Forbidden()

    # extract username from token
    username = decoded_token.get("preferred_username", email)

    # extract groups from token (can be in "groups" or "realm_access.roles")
    groups = decoded_token.get("groups", [])
    if not groups:
        # fallback to roles if no groups claim exists
        groups = decoded_token.get("realm_access", {}).get("roles", [])
    groups_str = ",".join(groups) if groups else ""

    # check permissions for individual apps
    if not installed_app.is_shared and email != installed_app.user_id:
        logger.info(
            "launch_authorize_permission_denied",
            extra={
                "event_name": "launchpad.auth.launch.authorize.reject",
                "reason_code": "APP_ACCESS_DENIED",
                "request_id": req_id,
                "correlation_id": corr_id,
                "app_name": installed_app.launchpad_app_name,
                "app_id": str(installed_app.app_id),
                "is_shared": installed_app.is_shared,
                "subject_hash": _mask_subject(email),
            },
        )
        raise Forbidden()

    response_headers = {
        # pass headers to a downstream app via traefik auth middleware
        HEADER_X_AUTH_REQUEST_EMAIL: email,
        HEADER_X_AUTH_REQUEST_USERNAME: username,
        HEADER_X_AUTH_REQUEST_GROUPS: groups_str,
    }

    logger.info(
        "launch_authorize_success",
        extra={
            "event_name": "launchpad.auth.launch.authorize.success",
            "reason_code": "AUTHORIZED",
            "request_id": req_id,
            "correlation_id": corr_id,
            "app_name": installed_app.launchpad_app_name,
            "app_id": str(installed_app.app_id),
            "is_shared": installed_app.is_shared,
        },
    )

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
            return await oauth.callback(request)
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
            logger.error(
                "auth_callback_post_token_validation_failed",
                extra={
                    "event_name": "launchpad.auth.callback.reject",
                    "reason_code": "TOKEN_VALIDATION_ERROR",
                    "error_type": type(e).__name__,
                },
            )
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
async def logout(response: Response, oauth: DepOauth) -> Response:
    oauth.logout(response)
    return Response()
