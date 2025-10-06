import logging
import os
from typing import Any, Annotated

import aiohttp
import backoff
import jwt
from aiohttp import ClientSession
from asyncache import cached
from cachetools import LRUCache
from fastapi import Depends
from starlette.requests import Request

from launchpad.auth.models import User
from launchpad.config import KeycloakConfig
from launchpad.errors import Unauthorized

logger = logging.getLogger(__name__)


async def auth_required(
    request: Request,
) -> User:
    """
    JWT authentication entry-point
    """
    decoded_token = await _token_from_request(request)
    try:
        email = decoded_token["email"]
    except KeyError:
        logger.error("Unable to extract `email` from the token")
        raise Unauthorized("Unable to authorize a user without an email")
    name = decoded_token.get("name") or ""

    # Extract roles from resource_access.frontend.roles
    groups = []
    resource_access = decoded_token.get("resource_access", {})
    frontend_access = resource_access.get("frontend", {})
    groups = frontend_access.get("roles", [])

    return User(id=email, email=email, name=name, groups=groups)


async def _token_from_request(request: Request) -> dict[str, Any]:
    try:
        _, access_token = request.headers["Authorization"].split(" ")
    except Exception:
        raise Unauthorized()
    return await token_from_string(
        http=request.app.http,
        keycloak_config=request.app.config.keycloak,
        access_token=access_token,
    )


async def token_from_string(
    http: ClientSession, keycloak_config: KeycloakConfig, access_token: str
) -> dict[str, Any]:
    """
    Extracts and decodes the token from the request
    """
    # get header so we can get a proper JWKS and determine the hashing algorithm
    try:
        header = jwt.get_unverified_header(access_token)
    except jwt.PyJWTError:
        logger.exception("can't get token header")
        raise Unauthorized()

    kid, alg = header["kid"], header["alg"]
    alg_obj = jwt.get_algorithm_by_name(alg)

    try:
        jwks = await _get_jwks(http=http, keycloak_config=keycloak_config, kid=kid)
    except Exception:
        logger.exception("can't obtain JWKS")
        raise Unauthorized()

    # get a secret key from a JWKS
    for key in jwks["keys"]:
        if key["kid"] == kid:
            secret_key = alg_obj.from_jwk(key)
            break
    else:
        logger.error(
            "unable to match a KID between a token and a JWKS",
            extra={"jwks": jwks, "access_token": access_token},
        )
        raise Unauthorized()

    try:
        token: dict[str, Any] = jwt.decode(
            access_token,
            secret_key,
            algorithms=[alg],
            issuer=f"{keycloak_config.url}/realms/{keycloak_config.realm}",
            audience="account",
        )
        return token
    except jwt.ExpiredSignatureError:
        raise Unauthorized()
    except jwt.PyJWTError:
        logger.exception("unable to decode a token")
        raise Unauthorized()


def cache_key_getter(*args: Any, **kwargs: str) -> str:
    """
    JWKS cache key getter which considers only the `kid`
    """
    return kwargs["kid"]


@backoff.on_exception(wait_gen=backoff.expo, exception=aiohttp.ClientError, max_tries=5)
@cached(cache=LRUCache(maxsize=32), key=cache_key_getter)  # type: ignore[misc]
async def _get_jwks(
    *,
    http: ClientSession,
    keycloak_config: KeycloakConfig,
    kid: str,
) -> Any:
    """
    Returns JWKS.
    Generally JWKS should not change, but it's still possible;
    Therefore, we cache the response by a token `kid`.
    """
    url = f"{keycloak_config.url}/realms/{keycloak_config.realm}/protocol/openid-connect/certs"
    response = await http.get(url, ssl=False)  # todo: see what we can do here with cert
    response.raise_for_status()
    return await response.json()


async def admin_role_required(
    request: Request,
) -> User:
    """
    JWT authentication with admin role check
    """
    user = await auth_required(request)
    if "admin" not in user.groups:
        logger.warning(
            f"User {user.email} attempted to access admin endpoint without admin role"
        )
        raise Unauthorized("Admin role required")
    return user


Auth = Annotated[User, Depends(auth_required)]
AdminAuth = Annotated[User, Depends(admin_role_required)]


async def admin_auth_required(
    request: Request,
) -> User:
    # use basic auth for admin endpoints
    # get admin password from env variable LAUNCHPAD_ADMIN_PASSWORD
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from starlette.status import HTTP_401_UNAUTHORIZED
    from starlette.exceptions import HTTPException

    security = HTTPBasic()
    credentials: HTTPBasicCredentials | None = await security(request)
    admin_password = os.environ.get("LAUNCHPAD_ADMIN_PASSWORD")
    if not credentials or not admin_password or credentials.password != admin_password:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return User(id="admin", email="admin", name="admin")
