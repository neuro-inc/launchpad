import hashlib
import hmac
import logging
import os
import time
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp
import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import (
    JSONResponse,
    PlainTextResponse,
    Response,
)

from launchpad.apps.storage import select_app_by_any_url
from launchpad.auth import (
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_ROLES,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_FORWARDED_HOST,
)
from launchpad.auth.dependencies import (
    _extract_bearer_token,
    decode_token_from_request,
    get_raw_token_from_request,
    token_from_string,
)
from launchpad.auth.oauth import DepOauth, OauthError
from launchpad.db.dependencies import Db
from launchpad.errors import Forbidden, Unauthorized


logger = logging.getLogger(__name__)
_LOG_HASH_KEY = os.urandom(32)

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
    return request.headers.get("x-request-id") or getattr(
        getattr(request, "state", None), "request_id", None
    )


def _correlation_id(request: Request) -> str | None:
    return (
        request.headers.get("x-correlation-id")
        or request.headers.get("x-amzn-trace-id")
        or getattr(getattr(request, "state", None), "correlation_id", None)
    )


def _classify_launch_url(host: str) -> str:
    if host.startswith("localhost") or host.startswith("127.0.0.1"):
        return "local"
    if host.endswith(".internal"):
        return "internal"
    return "public"


def _safe_token_meta(raw_token: str | None) -> dict[str, Any]:
    if not raw_token:
        return {
            "token_present": False,
            "token_valid": None,
            "token_expired": None,
            "token_ttl_seconds": None,
        }
    meta: dict[str, Any] = {
        "token_present": True,
        "token_valid": None,
        "token_expired": None,
        "token_ttl_seconds": None,
    }
    try:
        payload = jwt.decode(raw_token, options={"verify_signature": False})
    except jwt.PyJWTError:
        meta["token_claims_parse"] = "failed"
        return meta
    exp = payload.get("exp")
    now = int(time.time())
    if isinstance(exp, int):
        ttl = exp - now
        meta["token_ttl_seconds"] = max(ttl, 0)
        meta["token_expired"] = ttl <= 0
    return meta


def _mask_subject(subject: str) -> str:
    return hmac.new(
        _LOG_HASH_KEY,
        subject.strip().lower().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:12]


def _auth_log_base(
    request: Request,
    *,
    forwarded_host: str | None = None,
    installed_app: Any | None = None,
    token_meta: Mapping[str, Any] | None = None,
    token_valid: bool | None = None,
    issuer_valid: bool | None = None,
    audience_valid: bool | None = None,
    authorized_party_valid: bool | None = None,
    session_present: bool | None = None,
    session_valid: bool | None = None,
    user_id_hash: str | None = None,
    app_access_granted: bool | None = None,
    redirect_required: bool | None = None,
    redirect_target_type: str | None = None,
    forwardauth_result: str | None = None,
) -> dict[str, Any]:
    request_id = _request_id(request) or uuid4().hex
    correlation_id = _correlation_id(request) or request_id
    app_name = (
        getattr(installed_app, "launchpad_app_name", None) if installed_app else None
    )
    app_id = str(getattr(installed_app, "app_id", None)) if installed_app else None
    app_user_id = getattr(installed_app, "user_id", None) if installed_app else None
    return {
        "request_id": request_id,
        "correlation_id": correlation_id,
        "path": str(request.url.path),
        "method": request.method,
        "target_app_id": app_id,
        "target_app_name": app_name,
        "target_app_host": forwarded_host,
        "token_present": None,
        "token_valid": token_valid,
        "token_expired": None,
        "token_ttl_seconds": None,
        "issuer_valid": issuer_valid,
        "audience_valid": audience_valid,
        "authorized_party_valid": authorized_party_valid,
        "session_present": session_present,
        "session_valid": session_valid,
        "user_id_hash": user_id_hash,
        "app_access_granted": app_access_granted,
        "redirect_required": redirect_required,
        "redirect_target_type": redirect_target_type,
        "forwardauth_result": forwardauth_result,
        "app_owner_hash": _mask_subject(app_user_id) if app_user_id else None,
        **(dict(token_meta) if token_meta else {}),
    }


def _log_auth_decision(
    level: int,
    event: str,
    *,
    decision: str,
    reason_code: str,
    branch: str,
    request: Request,
    forwarded_host: str | None = None,
    installed_app: Any | None = None,
    token_meta: Mapping[str, Any] | None = None,
    token_valid: bool | None = None,
    issuer_valid: bool | None = None,
    audience_valid: bool | None = None,
    authorized_party_valid: bool | None = None,
    session_present: bool | None = None,
    session_valid: bool | None = None,
    user_id_hash: str | None = None,
    app_access_granted: bool | None = None,
    redirect_required: bool | None = None,
    redirect_target_type: str | None = None,
    forwardauth_result: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    payload = _auth_log_base(
        request,
        forwarded_host=forwarded_host,
        installed_app=installed_app,
        token_meta=token_meta,
        token_valid=token_valid,
        issuer_valid=issuer_valid,
        audience_valid=audience_valid,
        authorized_party_valid=authorized_party_valid,
        session_present=session_present,
        session_valid=session_valid,
        user_id_hash=user_id_hash,
        app_access_granted=app_access_granted,
        redirect_required=redirect_required,
        redirect_target_type=redirect_target_type,
        forwardauth_result=forwardauth_result,
    )
    payload.update(
        {
            "event": event,
            "event_name": event,
            "decision": decision,
            "reason_code": reason_code,
            "branch": branch,
        }
    )
    if extra:
        payload.update(dict(extra))
    logger.log(level, event, extra=payload)


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

    if azp == expected_client or expected_client in aud:
        return

    if azp is not None:
        logger.warning(
            "authorized_party_mismatch",
            extra={
                "event": "launchpad.auth.claims.checked",
                "event_name": "launchpad.auth.claims.checked",
                "reason_code": "AUTHORIZED_PARTY_INVALID",
                "expected_client_id": expected_client,
                "token_audience_count": len(aud),
                "authorized_party_present": True,
            },
        )
        raise Unauthorized(
            "Invalid token audience",
            reason_code="AUTHORIZED_PARTY_INVALID",
            branch="launchpad.auth.api._validate_token_audience.azp",
        )
    raise Unauthorized(
        "Invalid token audience",
        reason_code="AUDIENCE_INVALID",
        branch="launchpad.auth.api._validate_token_audience.aud",
    )


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
    forwarded_host = request.headers.get(HEADER_X_FORWARDED_HOST)
    if not forwarded_host:
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.forwardauth.denied",
            decision="deny",
            reason_code="FORWARDAUTH_HOST_MISSING",
            branch="launchpad.auth.api.view_post_authorize.forwarded_host_missing",
            request=request,
            redirect_required=False,
            forwardauth_result="deny",
        )
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.authorize.completed",
            decision="deny",
            reason_code="FORWARDAUTH_HOST_MISSING",
            branch="launchpad.auth.api.view_post_authorize.forwarded_host_missing",
            request=request,
            redirect_required=False,
            forwardauth_result="deny",
        )
        raise Unauthorized(
            "Missing ForwardAuth host header",
            reason_code="FORWARDAUTH_HOST_MISSING",
            branch="launchpad.auth.api.view_post_authorize.forwarded_host_missing",
        )
    app_url = f"https://{forwarded_host}"
    _log_auth_decision(
        logging.INFO,
        "launchpad.app_launch.started",
        decision="evaluate",
        reason_code="START",
        branch="launchpad.auth.api.view_post_authorize.start",
        request=request,
        forwarded_host=forwarded_host,
        redirect_required=False,
        extra={"launch_url_category": _classify_launch_url(forwarded_host)},
    )
    _log_auth_decision(
        logging.INFO,
        "launchpad.auth.authorize.started",
        decision="evaluate",
        reason_code="START",
        branch="launchpad.auth.api.view_post_authorize.start",
        request=request,
        forwarded_host=forwarded_host,
        redirect_required=False,
        extra={"launch_url_category": _classify_launch_url(forwarded_host)},
    )

    installed_app = await select_app_by_any_url(db=db, url=app_url)
    if installed_app is None:
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.forwardauth.denied",
            decision="deny",
            reason_code="TARGET_APP_UNRESOLVED",
            branch="launchpad.auth.api.view_post_authorize.app_lookup",
            request=request,
            forwarded_host=forwarded_host,
            redirect_required=False,
            forwardauth_result="deny",
        )
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.authorize.completed",
            decision="deny",
            reason_code="TARGET_APP_UNRESOLVED",
            branch="launchpad.auth.api.view_post_authorize.app_lookup",
            request=request,
            forwarded_host=forwarded_host,
            redirect_required=False,
            forwardauth_result="deny",
        )
        raise Forbidden()

    _log_auth_decision(
        logging.INFO,
        "launchpad.app_launch.target_resolved",
        decision="evaluate",
        reason_code="TARGET_APP_RESOLVED",
        branch="launchpad.auth.api.view_post_authorize.target_resolved",
        request=request,
        forwarded_host=forwarded_host,
        installed_app=installed_app,
        redirect_required=False,
    )

    raw_token = get_raw_token_from_request(request, oauth, allow_cookie=True)
    token_meta = _safe_token_meta(raw_token)
    _log_auth_decision(
        logging.INFO,
        "launchpad.auth.cookie.checked",
        decision="evaluate",
        reason_code="TOKEN_PRESENT" if raw_token else "TOKEN_MISSING",
        branch="launchpad.auth.api.view_post_authorize.cookie_checked",
        request=request,
        forwarded_host=forwarded_host,
        installed_app=installed_app,
        token_meta=token_meta,
        session_present=raw_token is not None,
        session_valid=None,
        redirect_required=False,
    )
    _log_auth_decision(
        logging.INFO,
        "launchpad.auth.token.validation_started",
        decision="evaluate",
        reason_code="TOKEN_VALIDATION_STARTED",
        branch="launchpad.auth.api.view_post_authorize.token_validation_started",
        request=request,
        forwarded_host=forwarded_host,
        installed_app=installed_app,
        token_meta=token_meta,
        session_present=raw_token is not None,
        session_valid=None,
        redirect_required=False,
    )
    try:
        decoded_token = await decode_token_from_request(request, oauth)
        await _validate_token_audience(decoded_token, request.app.config.keycloak)
    except Unauthorized as exc:
        reason_code = getattr(exc, "reason_code", None) or "UNKNOWN_AUTH_REDIRECT"
        branch = (
            getattr(exc, "branch", None)
            or "launchpad.auth.api.view_post_authorize.token_validation"
        )
        safe_meta = getattr(exc, "safe_meta", {}) or {}
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.token.validation_failed",
            decision="redirect_to_auth",
            reason_code=reason_code,
            branch=branch,
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=False,
            issuer_valid=False if reason_code == "ISSUER_INVALID" else None,
            audience_valid=False if reason_code == "AUDIENCE_INVALID" else None,
            authorized_party_valid=(
                False if reason_code == "AUTHORIZED_PARTY_INVALID" else None
            ),
            session_present=raw_token is not None,
            session_valid=False,
            redirect_required=True,
            redirect_target_type="keycloak",
            forwardauth_result="redirect",
            extra=safe_meta,
        )
        _log_auth_decision(
            logging.INFO,
            "launchpad.auth.reauthorization.required",
            decision="redirect_to_auth",
            reason_code=reason_code,
            branch=branch,
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=False,
            issuer_valid=False if reason_code == "ISSUER_INVALID" else None,
            audience_valid=False if reason_code == "AUDIENCE_INVALID" else None,
            authorized_party_valid=(
                False if reason_code == "AUTHORIZED_PARTY_INVALID" else None
            ),
            session_present=raw_token is not None,
            session_valid=False,
            redirect_required=True,
            redirect_target_type="keycloak",
            forwardauth_result="redirect",
            extra=safe_meta,
        )
        _log_auth_decision(
            logging.INFO,
            "launchpad.app_launch.redirect_prepared",
            decision="redirect_to_auth",
            reason_code=reason_code,
            branch=branch,
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=False,
            issuer_valid=False if reason_code == "ISSUER_INVALID" else None,
            audience_valid=False if reason_code == "AUDIENCE_INVALID" else None,
            authorized_party_valid=(
                False if reason_code == "AUTHORIZED_PARTY_INVALID" else None
            ),
            session_present=raw_token is not None,
            session_valid=False,
            redirect_required=True,
            redirect_target_type="keycloak",
            forwardauth_result="redirect",
        )
        _log_auth_decision(
            logging.INFO,
            "launchpad.auth.forwardauth.redirected",
            decision="redirect_to_auth",
            reason_code=reason_code,
            branch=branch,
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=False,
            issuer_valid=False if reason_code == "ISSUER_INVALID" else None,
            audience_valid=False if reason_code == "AUDIENCE_INVALID" else None,
            authorized_party_valid=(
                False if reason_code == "AUTHORIZED_PARTY_INVALID" else None
            ),
            session_present=raw_token is not None,
            session_valid=False,
            redirect_required=True,
            redirect_target_type="keycloak",
            forwardauth_result="redirect",
        )
        _log_auth_decision(
            logging.INFO,
            "launchpad.auth.authorize.completed",
            decision="redirect_to_auth",
            reason_code=reason_code,
            branch=branch,
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=False,
            issuer_valid=False if reason_code == "ISSUER_INVALID" else None,
            audience_valid=False if reason_code == "AUDIENCE_INVALID" else None,
            authorized_party_valid=(
                False if reason_code == "AUTHORIZED_PARTY_INVALID" else None
            ),
            session_present=raw_token is not None,
            session_valid=False,
            redirect_required=True,
            redirect_target_type="keycloak",
            forwardauth_result="redirect",
        )
        return oauth.redirect(original_redirect_uri=app_url)

    _log_auth_decision(
        logging.INFO,
        "launchpad.auth.token.validation_succeeded",
        decision="evaluate",
        reason_code="TOKEN_VALID",
        branch="launchpad.auth.api.view_post_authorize.token_valid",
        request=request,
        forwarded_host=forwarded_host,
        installed_app=installed_app,
        token_meta=token_meta,
        token_valid=True,
        issuer_valid=True,
        audience_valid=True,
        authorized_party_valid=True,
        session_present=raw_token is not None,
        session_valid=True,
        redirect_required=False,
    )

    try:
        email = str(decoded_token["email"])
    except KeyError:
        logger.error("Token missing required 'email' claim; denying access")
        raise Forbidden("Token is missing required 'email' claim")
    user_id_hash = _mask_subject(email)

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
    if not installed_app.is_shared and email != installed_app.user_id:
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.app_access.checked",
            decision="deny",
            reason_code="APP_ACCESS_DENIED",
            branch="launchpad.auth.api.view_post_authorize.app_access",
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=True,
            issuer_valid=True,
            audience_valid=True,
            authorized_party_valid=True,
            session_present=raw_token is not None,
            session_valid=True,
            user_id_hash=user_id_hash,
            app_access_granted=False,
            redirect_required=False,
            forwardauth_result="deny",
        )
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.forwardauth.denied",
            decision="deny",
            reason_code="APP_ACCESS_DENIED",
            branch="launchpad.auth.api.view_post_authorize.app_access",
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=True,
            issuer_valid=True,
            audience_valid=True,
            authorized_party_valid=True,
            session_present=raw_token is not None,
            session_valid=True,
            user_id_hash=user_id_hash,
            app_access_granted=False,
            redirect_required=False,
            forwardauth_result="deny",
        )
        _log_auth_decision(
            logging.WARNING,
            "launchpad.auth.authorize.completed",
            decision="deny",
            reason_code="APP_ACCESS_DENIED",
            branch="launchpad.auth.api.view_post_authorize.app_access",
            request=request,
            forwarded_host=forwarded_host,
            installed_app=installed_app,
            token_meta=token_meta,
            token_valid=True,
            session_present=raw_token is not None,
            session_valid=True,
            user_id_hash=user_id_hash,
            app_access_granted=False,
            redirect_required=False,
            forwardauth_result="deny",
        )
        raise Forbidden()

    response_headers: dict[str, str] = {
        # pass headers to a downstream app via traefik auth middleware
        HEADER_X_AUTH_REQUEST_EMAIL: email,
        HEADER_X_AUTH_REQUEST_USERNAME: username,
        HEADER_X_AUTH_REQUEST_GROUPS: groups_str,
        HEADER_X_AUTH_REQUEST_ROLES: roles_str,
    }

    _log_auth_decision(
        logging.INFO,
        "launchpad.auth.forwardauth.allowed",
        decision="allow",
        reason_code="AUTHORIZED",
        branch="launchpad.auth.api.view_post_authorize.allow",
        request=request,
        forwarded_host=forwarded_host,
        installed_app=installed_app,
        token_meta=token_meta,
        token_valid=True,
        issuer_valid=True,
        audience_valid=True,
        authorized_party_valid=True,
        session_present=raw_token is not None,
        session_valid=True,
        user_id_hash=user_id_hash,
        app_access_granted=True,
        redirect_required=False,
        forwardauth_result="allow",
        extra={"forwardauth_headers_present": True},
    )
    _log_auth_decision(
        logging.INFO,
        "launchpad.auth.authorize.completed",
        decision="allow",
        reason_code="AUTHORIZED",
        branch="launchpad.auth.api.view_post_authorize.allow",
        request=request,
        forwarded_host=forwarded_host,
        installed_app=installed_app,
        token_meta=token_meta,
        token_valid=True,
        session_present=raw_token is not None,
        session_valid=True,
        user_id_hash=user_id_hash,
        app_access_granted=True,
        redirect_required=False,
        forwardauth_result="allow",
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
