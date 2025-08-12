import logging
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
    return User(
        id=decoded_token["email"],
        email=decoded_token["email"],
        name=decoded_token["name"],
    )


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
    response = await http.get(  # type: ignore[call-arg]
        url, verify_ssl=False
    )  # todo: see what we can do here with cert
    response.raise_for_status()
    return await response.json()


Auth = Annotated[User, Depends(auth_required)]
