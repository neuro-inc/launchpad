from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from launchpad.apps.service import AppService
from launchpad.auth import (
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_ROLES,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_FORWARDED_HOST,
    HEADER_X_FORWARDED_URI,
)
from launchpad.auth.api import _is_auth_bypass_path, view_post_authorize
from launchpad.errors import Unauthorized


_PUBLIC_PREFIXES = ["/public", "/api/webhooks"]
_REFUSED_CHARACTERS = {
    "percent-encoded": "%",
    "backslash": "\\",
    "semicolon": ";",
    "colon": ":",
    "space": " ",
    "tab": "\t",
    "hash": "#",
    "quote": '"',
    "angle-bracket": "<",
    "caret": "^",
    "backtick": "`",
    "brace": "{",
    "pipe": "|",
    "square-bracket": "[",
    "non-ascii": "\u00e9",
}


@pytest.fixture
def mock_request() -> MagicMock:
    request = MagicMock()
    request.headers = {HEADER_X_FORWARDED_HOST: "example.test"}
    request.app = MagicMock()
    request.app.config = SimpleNamespace(
        auth_bypass_path_prefixes=["/public", "/api/webhooks"]
    )
    return request


def _installed_app() -> SimpleNamespace:
    return SimpleNamespace(app_id=uuid4(), is_shared=True, user_id="owner@example.test")


@pytest.mark.parametrize(
    ("decoded_token", "expected_groups", "expected_roles"),
    [
        (
            {"email": "user@example.test", "groups": ["g1", "g2"]},
            "g1,g2",
            "",
        ),
        (
            {
                "email": "user@example.test",
                "realm_access": {"roles": ["r1", "r2"]},
            },
            "",
            "r1,r2",
        ),
        (
            {
                "email": "user@example.test",
                "groups": ["g1"],
                "realm_access": {"roles": ["r1"]},
            },
            "g1",
            "r1",
        ),
        (
            {"email": "user@example.test"},
            "",
            "",
        ),
    ],
)
async def test_view_post_authorize_forwards_groups_and_roles_separately(
    mock_request: MagicMock,
    decoded_token: dict[str, object],
    expected_groups: str,
    expected_roles: str,
) -> None:
    app_service = MagicMock(spec=AppService)
    oauth = MagicMock()
    oauth.covers_hostname.return_value = True

    with (
        patch.object(
            app_service, "resolve_app_for_authorization", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.dependencies.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.return_value = decoded_token

        response = await view_post_authorize(
            request=mock_request,
            app_service=app_service,
            oauth=oauth,
            static_hostname_auth=MagicMock(),
        )

    assert response.status_code == 200
    assert response.headers[HEADER_X_AUTH_REQUEST_EMAIL] == "user@example.test"
    assert response.headers[HEADER_X_AUTH_REQUEST_USERNAME] == "user@example.test"
    assert response.headers[HEADER_X_AUTH_REQUEST_GROUPS] == expected_groups
    assert response.headers[HEADER_X_AUTH_REQUEST_ROLES] == expected_roles


@pytest.mark.parametrize(
    ("path", "prefixes", "expected"),
    [
        ("/public", ["/public"], True),
        ("/public/file.txt", ["/public"], True),
        ("/api/webhooks/v1", ["/api/webhooks"], True),
        ("/publicity", ["/public"], False),
        ("/api/webhooksx", ["/api/webhooks"], False),
        ("/x", ["/public", "/api/webhooks"], False),
        ("/public", ["public/"], True),
        ("/", ["/"], True),
        ("/", ["/public"], False),
    ],
)
def test_is_auth_bypass_path(path: str, prefixes: list[str], expected: bool) -> None:
    assert _is_auth_bypass_path(path, prefixes) is expected


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/public", id="prefix"),
        pytest.param("/public/", id="prefix-trailing-slash"),
        pytest.param("/public/file.txt", id="file"),
        pytest.param("/public/assets/app-1.2_3~x.js", id="unreserved"),
        pytest.param("/public/logo@2x.png", id="at-sign"),
        pytest.param("/public/file(1).png", id="parentheses"),
        pytest.param("/public/a+b.txt", id="plus"),
        pytest.param("/public/!$&'()*+,=@", id="sub-delimiters"),
        pytest.param("/public/file.txt?v=1", id="query"),
        pytest.param("/public?v=1", id="prefix-query"),
        pytest.param("/api/webhooks", id="second-prefix"),
        pytest.param("/api/webhooks/incoming", id="second-prefix-file"),
        pytest.param(
            "/api/webhooks/incoming?id=1&source=a/b", id="second-prefix-query"
        ),
    ],
)
def test_is_auth_bypass_path_accepts_canonical_paths_under_prefix(path: str) -> None:
    assert _is_auth_bypass_path(path, _PUBLIC_PREFIXES) is True


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("", id="empty"),
        pytest.param("?", id="query-only"),
        pytest.param("public/file.txt", id="relative"),
        pytest.param("/publicx", id="longer-name"),
        pytest.param("/api/webhooksx/incoming", id="second-prefix-longer-name"),
        pytest.param("/PUBLIC/file.txt", id="upper-case"),
        pytest.param("/other?next=/public/file.txt", id="prefix-in-query"),
        pytest.param("/public//file.txt", id="empty-segment"),
        pytest.param("//public/file.txt", id="empty-first-segment"),
        *(
            pytest.param(f"/public/{segment}", id=f"dot-segment-last-{len(segment)}")
            for segment in (".", "..")
        ),
        *(
            pytest.param(f"/public/a/{segment}/b", id=f"dot-segment-{len(segment)}")
            for segment in (".", "..")
        ),
        *(
            pytest.param(f"/public/a{character}b", id=name)
            for name, character in _REFUSED_CHARACTERS.items()
        ),
        *(
            pytest.param(f"/public{character}/a", id=f"{name}-after-prefix")
            for name, character in _REFUSED_CHARACTERS.items()
        ),
    ],
)
def test_is_auth_bypass_path_requires_canonical_path_under_prefix(path: str) -> None:
    assert _is_auth_bypass_path(path, _PUBLIC_PREFIXES) is False


async def test_view_post_authorize_requires_token_for_non_canonical_paths(
    mock_request: MagicMock,
) -> None:
    app_service = MagicMock(spec=AppService)
    oauth = MagicMock()
    oauth.covers_hostname.return_value = True
    mock_request.headers[HEADER_X_FORWARDED_URI] = "/public/a/../b"

    with (
        patch.object(
            app_service, "resolve_app_for_authorization", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.dependencies.decode_token_from_request",
            new=AsyncMock(side_effect=Unauthorized()),
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()

        response = await view_post_authorize(
            request=mock_request,
            app_service=app_service,
            oauth=oauth,
            static_hostname_auth=MagicMock(),
        )

    mock_decode.assert_awaited_once()
    oauth.redirect.assert_called_once_with(original_redirect_uri="https://example.test")
    assert response is oauth.redirect.return_value


async def test_view_post_authorize_bypasses_redirect_for_configured_paths(
    mock_request: MagicMock,
) -> None:
    app_service = MagicMock(spec=AppService)
    oauth = MagicMock()
    oauth.covers_hostname.return_value = True
    mock_request.headers[HEADER_X_FORWARDED_URI] = "/api/webhooks/incoming"

    with (
        patch.object(
            app_service, "resolve_app_for_authorization", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.dependencies.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.side_effect = AssertionError(
            "decode_token_from_request should not be called for bypass paths"
        )

        response = await view_post_authorize(
            request=mock_request,
            app_service=app_service,
            oauth=oauth,
            static_hostname_auth=MagicMock(),
        )

    assert response.status_code == 200
    oauth.redirect.assert_not_called()


async def test_view_post_authorize_does_not_bypass_when_prefixes_disabled(
    mock_request: MagicMock,
) -> None:
    app_service = MagicMock(spec=AppService)
    oauth = MagicMock()
    oauth.covers_hostname.return_value = True
    mock_request.headers[HEADER_X_FORWARDED_URI] = "/api/webhooks/incoming"
    mock_request.app.config.auth_bypass_path_prefixes = []

    with (
        patch.object(
            app_service, "resolve_app_for_authorization", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.dependencies.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.return_value = {"email": "user@example.test"}

        response = await view_post_authorize(
            request=mock_request,
            app_service=app_service,
            oauth=oauth,
            static_hostname_auth=MagicMock(),
        )

    assert response.status_code == 200
    assert response.headers[HEADER_X_AUTH_REQUEST_EMAIL] == "user@example.test"
