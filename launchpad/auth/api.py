import logging

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

from launchpad.apps.storage import select_app
from launchpad.auth import (
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_FORWARDED_HOST,
)
from launchpad.auth.dependencies import token_from_string
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

    try:
        async with request.app.http.post(token_url, data=data, ssl=False) as response:
            response.raise_for_status()
            token_data = await response.json()
            return JSONResponse(content=token_data)
    except Exception as e:
        logger.error(f"Failed to obtain token from Keycloak: {e}")
        raise Unauthorized("Failed to authenticate with provided credentials")


@auth_router.get("/authorize", status_code=200)
async def view_post_authorize(
    request: Request,
    db: Db,
    oauth: DepOauth,
) -> Response:
    app_url = f"https://{request.headers[HEADER_X_FORWARDED_HOST]}"
    installed_app = await select_app(db=db, url=app_url)
    if installed_app is None:
        logger.info(f"Unable to find installed app by url: {app_url}")
        raise Forbidden()

    if installed_app.is_internal:
        logger.info("access to an internal app is forbidden")
        raise Forbidden()

    access_token = oauth.get_token_from_cookie(request)
    if not access_token:
        logger.info("no access token present. redirecting to keycloak")
        return oauth.redirect(original_redirect_uri=app_url)

    try:
        decoded_token = await token_from_string(
            http=request.app.http,
            keycloak_config=request.app.config.keycloak,
            access_token=access_token,
        )
    except Unauthorized:
        logger.info("unable to decode token. redirecting to keycloak")
        return oauth.redirect(original_redirect_uri=app_url)

    logger.debug(f"Decoded token keys: {list(decoded_token.keys())}")
    logger.debug(f"Token realm_access: {decoded_token.get('realm_access')}")
    logger.debug(f"Token groups: {decoded_token.get('groups')}")

    try:
        email = decoded_token["email"]
    except KeyError:
        logger.error("malformed token. forbidden")
        raise Forbidden()

    # extract username from token
    username = decoded_token.get("preferred_username", email)

    # extract groups from token (can be in "groups" or "realm_access.roles")
    groups = decoded_token.get("groups", [])
    if not groups:
        # fallback to roles if no groups claim exists
        groups = decoded_token.get("realm_access", {}).get("roles", [])
    groups_str = ",".join(groups) if groups else ""

    logger.debug(
        f"Authorizing user - Email: {email}, Username: {username}, Groups: {groups_str}"
    )

    # check permissions for individual apps
    if not installed_app.is_shared and email != installed_app.user_id:
        logger.info(f"permission denied for user {email}")
        raise Forbidden()

    response_headers = {
        # pass headers to a downstream app via traefik auth middleware
        HEADER_X_AUTH_REQUEST_EMAIL: email,
        HEADER_X_AUTH_REQUEST_USERNAME: username,
        HEADER_X_AUTH_REQUEST_GROUPS: groups_str,
    }

    logger.debug(f"Returning auth headers: {response_headers}")

    return PlainTextResponse(
        "OK",
        status_code=200,
        headers=response_headers,
    )


@auth_router.get("/callback", status_code=200)
async def callback(
    request: Request,
    oauth: DepOauth,
) -> Response:
    try:
        return await oauth.callback(request)
    except OauthError as e:
        raise Forbidden(str(e))


@auth_router.post("/logout", status_code=200)
async def logout(response: Response, oauth: DepOauth) -> Response:
    oauth.logout(response)
    return Response()
