"""
Middleware to automatically set the launchpad-token cookie when a valid
Bearer token is present in the Authorization header.

This ensures that even when the frontend uses NextAuth.js or other auth mechanisms,
the launchpad-token cookie will be set automatically on the first authenticated request.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from launchpad.auth.dependencies import token_from_string
from launchpad.auth.oauth import COOKIE_TOKEN


logger = logging.getLogger(__name__)


class TokenCookieMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically sets the launchpad-token cookie when a valid
    Bearer token is detected in the Authorization header.

    This is useful when the frontend uses a different authentication mechanism
    (e.g., NextAuth.js) but downstream applications still need the launchpad-token cookie.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip cookie setting for:
        # - Auth endpoints (they handle cookies themselves)
        # - Static/OpenAPI endpoints
        # - Requests that already have the cookie
        skip_paths = [
            "/auth/",
            "/openapi/",
            "/ping",
            "/branding/",
        ]

        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Check if cookie is already present
        if request.cookies.get(COOKIE_TOKEN):
            return await call_next(request)

        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        access_token = auth_header.split(" ", 1)[1]
        if not access_token:
            return await call_next(request)

        # Process the request first
        response = await call_next(request)

        # Try to validate the token and set cookie
        try:
            await token_from_string(
                http=request.app.http,
                keycloak_config=request.app.config.keycloak,
                access_token=access_token,
            )

            # Get cookie domain from config
            apolo_cfg = getattr(request.app.config, "apolo", None)
            if apolo_cfg:
                base_domain = getattr(apolo_cfg, "base_domain", None)
                if base_domain:
                    cookie_domain = f".{base_domain}"
                    response.set_cookie(
                        key=COOKIE_TOKEN,
                        value=access_token,
                        domain=cookie_domain,
                        secure=True,
                        httponly=True,
                    )
                    logger.debug(
                        f"launchpad-token cookie set automatically for path: {request.url.path}"
                    )
        except Exception as e:
            # Don't fail the request if cookie setting fails
            logger.warning(f"Failed to set launchpad-token cookie: {e}")

        return response
