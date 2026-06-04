from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launchpad.auth import (
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_ROLES,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_FORWARDED_HOST,
    HEADER_X_FORWARDED_URI,
)
from launchpad.auth.api import _is_auth_bypass_path, view_post_authorize
from launchpad.errors import Forbidden


@pytest.fixture
def mock_request() -> MagicMock:
    request = MagicMock()
    request.headers = {HEADER_X_FORWARDED_HOST: "example.test"}
    request.app = MagicMock()
    request.app.config = SimpleNamespace(
        auth_bypass_path_prefixes=["/public", "/api/webhooks"],
        keycloak=SimpleNamespace(
            idp_hint=None,
            required_identity_source=None,
            required_identity_group=None,
        ),
    )
    return request


def _installed_app() -> SimpleNamespace:
    return SimpleNamespace(is_shared=True, user_id="owner@example.test")


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
    db = MagicMock()
    oauth = MagicMock()

    with (
        patch(
            "launchpad.auth.api.select_app_by_any_url", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.api.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.return_value = decoded_token

        response = await view_post_authorize(request=mock_request, db=db, oauth=oauth)

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
    ],
)
def test_is_auth_bypass_path(path: str, prefixes: list[str], expected: bool) -> None:
    assert _is_auth_bypass_path(path, prefixes) is expected


async def test_view_post_authorize_bypasses_redirect_for_configured_paths(
    mock_request: MagicMock,
) -> None:
    db = MagicMock()
    oauth = MagicMock()
    mock_request.headers[HEADER_X_FORWARDED_URI] = "/api/webhooks/incoming"

    with (
        patch(
            "launchpad.auth.api.select_app_by_any_url", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.api.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.side_effect = AssertionError(
            "decode_token_from_request should not be called for bypass paths"
        )

        response = await view_post_authorize(request=mock_request, db=db, oauth=oauth)

    assert response.status_code == 200
    oauth.redirect.assert_not_called()


async def test_view_post_authorize_does_not_bypass_when_prefixes_disabled(
    mock_request: MagicMock,
) -> None:
    db = MagicMock()
    oauth = MagicMock()
    mock_request.headers[HEADER_X_FORWARDED_URI] = "/api/webhooks/incoming"
    mock_request.app.config.auth_bypass_path_prefixes = []

    with (
        patch(
            "launchpad.auth.api.select_app_by_any_url", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.api.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.return_value = {"email": "user@example.test"}

        response = await view_post_authorize(request=mock_request, db=db, oauth=oauth)

    assert response.status_code == 200
    assert response.headers[HEADER_X_AUTH_REQUEST_EMAIL] == "user@example.test"


async def test_view_post_authorize_requires_procore_identity_when_configured(
    mock_request: MagicMock,
) -> None:
    mock_request.app.config.keycloak.required_identity_source = "procore"
    mock_request.app.config.keycloak.required_identity_group = "/procore-users"
    db = MagicMock()
    oauth = MagicMock()

    with (
        patch(
            "launchpad.auth.api.select_app_by_any_url", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.api.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.return_value = {
            "email": "user@example.test",
            "groups": ["/procore-users"],
            "realm_access": {"roles": ["r1"]},
        }

        with pytest.raises(Forbidden, match="ProCore identity is required"):
            await view_post_authorize(request=mock_request, db=db, oauth=oauth)


async def test_view_post_authorize_skips_procore_for_regular_user(
    mock_request: MagicMock,
) -> None:
    mock_request.app.config.keycloak.required_identity_source = "procore"
    mock_request.app.config.keycloak.required_identity_group = "/procore-users"
    db = MagicMock()
    oauth = MagicMock()

    with (
        patch(
            "launchpad.auth.api.select_app_by_any_url", new=AsyncMock()
        ) as mock_select_app,
        patch(
            "launchpad.auth.api.decode_token_from_request", new=AsyncMock()
        ) as mock_decode,
    ):
        mock_select_app.return_value = _installed_app()
        mock_decode.return_value = {
            "email": "user@example.test",
            "groups": ["/support-users"],
            "realm_access": {"roles": ["r1"]},
        }

        response = await view_post_authorize(request=mock_request, db=db, oauth=oauth)

    assert response.status_code == 200
