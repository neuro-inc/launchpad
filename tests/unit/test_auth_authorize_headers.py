from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launchpad.auth import (
    HEADER_X_AUTH_REQUEST_EMAIL,
    HEADER_X_AUTH_REQUEST_GROUPS,
    HEADER_X_AUTH_REQUEST_ROLES,
    HEADER_X_AUTH_REQUEST_USERNAME,
    HEADER_X_FORWARDED_HOST,
)
from launchpad.auth.api import view_post_authorize


@pytest.fixture
def mock_request() -> MagicMock:
    request = MagicMock()
    request.headers = {HEADER_X_FORWARDED_HOST: "example.test"}
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
