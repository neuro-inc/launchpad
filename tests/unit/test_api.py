"""Unit tests for the public API endpoints in ``launchpad.api``.

Only simple unit tests here — integration tests exercise the full
application elsewhere in the test suite.
"""

import sys
from types import ModuleType


# The module `magic` (libmagic wrapper) is an optional native dependency and
# may not be available in the unit test environment. The production module
# imports `magic` at import time which would raise ImportError here. To keep
# this test a fast unit test we provide a lightweight stub ModuleType for
# ``magic`` prior to importing `launchpad.api`. Using ModuleType satisfies
# mypy's expectations for entries in ``sys.modules``.
_magic_mod = ModuleType("magic")


class _DummyMagic:
    def __init__(self, mime: bool = True) -> None:  # pragma: no cover - trivial
        pass

    def from_file(self, _path: str) -> None:  # pragma: no cover - trivial
        return None


setattr(_magic_mod, "Magic", _DummyMagic)
sys.modules.setdefault("magic", _magic_mod)

from starlette.responses import RedirectResponse

from launchpad.api import root


async def test_root_auth_start_delegates() -> None:
    """The root-mounted `/auth/start` handler should delegate to
    the Oauth.start_auth implementation and return a RedirectResponse.
    """
    # Lightweight local construction of an Oauth instance to avoid
    # importing the heavy test fixtures from other modules.
    from unittest.mock import MagicMock

    from aiohttp import ClientSession
    from starlette.requests import Request
    from yarl import URL

    from launchpad.auth.oauth import Oauth
    from launchpad.config import KeycloakConfig

    mock_http = MagicMock(spec=ClientSession)
    keycloak_config = KeycloakConfig(
        url=URL("http://mock-keycloak.com"),
        realm="mock-realm",
        client_id="mock-client-id",
    )

    oauth_instance = Oauth(
        http=mock_http,
        keycloak_config=keycloak_config,
        cookie_domain="mock-cookie.com",
        launchpad_domain="mock-launchpad.com",
    )

    mock_request = MagicMock(spec=Request)
    mock_request.url = URL("https://example.com/foo")

    from launchpad.api import start_auth as root_start

    response = await root_start(mock_request, oauth_instance)
    assert isinstance(response, RedirectResponse)
    redirect_url = URL(response.headers["location"])
    assert redirect_url.path.endswith("/auth")


def test_root_redirects_to_auth_start() -> None:
    """Root handler should redirect to the interactive auth start path.

    This is a small, fast unit test that doesn't create a running app.
    """
    response = root()

    assert isinstance(response, RedirectResponse)
    # The root implementation redirects to the relative path
    # "/auth/start" so the location header should contain it.
    assert response.headers.get("location") == "/auth/start"
