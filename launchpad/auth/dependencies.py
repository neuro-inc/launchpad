import logging
import os
from typing import Annotated, Any, Optional

import aiohttp
import backoff
import jwt
from aiohttp import ClientSession
from asyncache import cached
from cachetools import LRUCache
from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

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


def _extract_bearer_token(auth_header: Optional[str]) -> Optional[str]:
    """Extract bearer token from Authorization header.

    Returns the token string or None if header is missing/invalid.
    """
    if not auth_header:
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer":
        return None

    token = token.strip()
    return token or None


def get_raw_token_from_request(
    request: Request, oauth: Any | None = None, allow_cookie: bool = True
) -> Optional[str]:
    """Return raw access token from cookie or Authorization header.

    Preference: cookie (if allowed and oauth provided) -> Authorization header.

    Args:
        request: Starlette request.
        oauth: Optional oauth helper providing `get_token_from_cookie`.
        allow_cookie: Whether to check cookie first.

    Returns:
        The raw token string if present, otherwise None.
    """
    if allow_cookie and oauth is not None:
        try:
            token = oauth.get_token_from_cookie(request)
            if token is not None:
                # Ensure we return a str (oauth implementations may return Any)
                return token if isinstance(token, str) else str(token)
        except Exception:
            logger.debug("oauth.get_token_from_cookie raised", exc_info=True)

    auth_header = request.headers.get("Authorization")
    try:
        token = _extract_bearer_token(auth_header)
        if token:
            return token
    except Exception:
        logger.debug("error while parsing Authorization header", exc_info=True)

    return None


async def decode_token_from_request(
    request: Request, oauth: Any | None = None, allow_cookie: bool = True
) -> dict[str, Any]:
    """Extract and decode token from request.

    Args:
        request: Starlette request.
        oauth: Optional oauth helper.
        allow_cookie: Whether to check cookie first.

    Returns:
        Decoded token payload.

    Raises:
        Unauthorized: If token is missing or invalid.
    """
    raw_token = get_raw_token_from_request(
        request, oauth=oauth, allow_cookie=allow_cookie
    )
    if not raw_token:
        raise Unauthorized("Unauthorized")

    return await token_from_string(
        http=request.app.http,
        keycloak_config=request.app.config.keycloak,
        access_token=raw_token,
    )


async def _token_from_request(request: Request) -> dict[str, Any]:
    """Extract bearer token from Authorization header and return decoded payload."""
    raw_token = _extract_bearer_token(request.headers.get("Authorization"))
    if not raw_token:
        raise Unauthorized("Unathorized")
    return await token_from_string(
        http=request.app.http,
        keycloak_config=request.app.config.keycloak,
        access_token=raw_token,
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
@cached(cache=LRUCache(maxsize=32), key=cache_key_getter)  # type: ignore
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
