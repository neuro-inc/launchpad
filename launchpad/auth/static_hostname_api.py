from datetime import UTC, datetime
from typing import Any, Mapping
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse, Response

from launchpad.apps.models import InstalledApp
from launchpad.apps.service import AppService, DepAppService
from launchpad.auth import AUTH_REDIRECT_HEADERS, HEADER_X_FORWARDED_URI
from launchpad.auth.dependencies import (
    authorize_app_email,
    get_raw_token_from_request,
    resolve_app_for_authorization,
    token_from_string,
)
from launchpad.auth.models import AliasSession
from launchpad.auth.oauth import DepOauth, Oauth
from launchpad.auth.static_hostname import (
    LOGIN_TTL_SECONDS,
    DepStaticHostnameAuth,
    StaticHostnameAuthService,
)
from launchpad.errors import Forbidden, Unauthorized


static_hostname_router = APIRouter()


def _redirect_with_static_hostname_session(
    app_url: str, session: str, static_hostname_auth: StaticHostnameAuthService
) -> RedirectResponse:
    response = RedirectResponse(f"{app_url}/", headers=AUTH_REDIRECT_HEADERS)
    response.set_cookie(
        static_hostname_auth.session_cookie,
        session,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        static_hostname_auth.nonce_cookie,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


async def begin_static_hostname_login(
    hostname: str,
    app_id: UUID,
    oauth: Oauth,
    static_hostname_auth: StaticHostnameAuthService,
) -> RedirectResponse:
    login, nonce = await static_hostname_auth.begin(hostname, app_id)
    response = RedirectResponse(
        f"{oauth.auth_base_url}/static-hostname/start?{urlencode({'login': login})}",
        headers=AUTH_REDIRECT_HEADERS,
    )
    response.set_cookie(
        static_hostname_auth.nonce_cookie,
        nonce,
        max_age=LOGIN_TTL_SECONDS,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


async def handle_static_hostname_handoff(
    request: Request,
    app_id: UUID,
    static_hostname_auth: StaticHostnameAuthService,
    *,
    hostname: str,
    is_cross_domain: bool,
) -> RedirectResponse | None:
    if not is_cross_domain:
        return None
    forwarded_uri = urlsplit(request.headers.get(HEADER_X_FORWARDED_URI, ""))
    if forwarded_uri.path != static_hostname_auth.callback_path:
        return None
    grants = parse_qs(forwarded_uri.query).get("grant", [])
    nonce = request.cookies.get(static_hostname_auth.nonce_cookie)
    if len(grants) != 1 or not nonce:
        raise Forbidden()
    session = await static_hostname_auth.redeem(grants[0], nonce, hostname, app_id)
    return _redirect_with_static_hostname_session(
        f"https://{hostname}", session, static_hostname_auth
    )


async def _resolve_pending_login_app(
    app_service: AppService, pending_login: AliasSession
) -> InstalledApp:
    installed_app = await resolve_app_for_authorization(
        app_service, pending_login.hostname
    )
    if installed_app is None or installed_app.app_id != pending_login.app_id:
        raise Forbidden()
    return installed_app


def _token_expires_at(token: Mapping[str, Any]) -> datetime:
    expiry = token.get("exp")
    if not isinstance(expiry, (int, float)) or isinstance(expiry, bool):
        raise Forbidden()
    try:
        expires_at = datetime.fromtimestamp(expiry, UTC)
    except (ValueError, OverflowError, OSError):
        raise Forbidden() from None
    if expires_at <= datetime.now(UTC):
        raise Forbidden()
    return expires_at


@static_hostname_router.get("/static-hostname/start")
async def start_static_hostname_login(
    login: str,
    app_service: DepAppService,
    static_hostname_auth: DepStaticHostnameAuth,
    oauth: DepOauth,
) -> Response:
    pending_login = await static_hostname_auth.read_login(login)
    await _resolve_pending_login_app(app_service, pending_login)
    response = oauth.redirect(
        original_redirect_uri=f"{oauth.auth_base_url}/static-hostname/finish?{urlencode({'login': login})}"
    )
    response.headers.update(AUTH_REDIRECT_HEADERS)
    return response


@static_hostname_router.get("/static-hostname/finish")
async def finish_static_hostname_login(
    request: Request,
    login: str,
    app_service: DepAppService,
    static_hostname_auth: DepStaticHostnameAuth,
    oauth: DepOauth,
) -> Response:
    pending_login = await static_hostname_auth.read_login(login)
    installed_app = await _resolve_pending_login_app(app_service, pending_login)
    token = get_raw_token_from_request(request, oauth)
    if token is None:
        raise Unauthorized()
    decoded = await token_from_string(
        request.app.http, request.app.config.keycloak, token
    )
    email = authorize_app_email(installed_app, decoded)
    expires_at = _token_expires_at(decoded)
    grant = await static_hostname_auth.issue(login, token, expires_at, email)
    return RedirectResponse(
        f"https://{pending_login.hostname}{static_hostname_auth.callback_path}?{urlencode({'grant': grant})}",
        headers=AUTH_REDIRECT_HEADERS,
    )
