import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from launchpad.apps.models import InstalledApp
from launchpad.apps.storage import delete_app, insert_app, select_app


@pytest.fixture
def mock_db_session() -> MagicMock:
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock the execute method to return a mock cursor
    mock_cursor = MagicMock()
    mock_cursor.scalar_one_or_none = MagicMock()
    mock_cursor.scalar = MagicMock()

    mock_session.execute.return_value = mock_cursor
    return mock_session


@pytest.fixture
def app_id() -> UUID:
    return uuid.uuid4()


async def test_select_app_found(mock_db_session: MagicMock, app_id: UUID) -> None:
    mock_app_instance = MagicMock(spec=InstalledApp)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_app_instance
    )

    result = await select_app(mock_db_session, id=app_id)
    assert result == mock_app_instance
    mock_db_session.execute.assert_called_once()


async def test_select_app_not_found(mock_db_session: MagicMock, app_id: UUID) -> None:
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

    result = await select_app(mock_db_session, id=app_id)

    assert result is None
    mock_db_session.execute.assert_called_once()


async def test_insert_app_success(mock_db_session: MagicMock, app_id: UUID) -> None:
    app_data: dict[str, Any] = {
        "app_id": app_id,
        "app_name": "test-app",
        "launchpad_app_name": "test-launchpad-app",
        "is_internal": False,
        "is_shared": False,
        "user_id": "test-user",
        "url": "http://test.com",
        "template_name": "test-template",
    }
    mock_db_session.add.return_value = None
    mock_db_session.flush.return_value = None

    # Mock cursor.scalar() to return an InstalledApp instance
    mock_db_session.execute.return_value.scalar.return_value = InstalledApp(
        id=uuid.uuid4(),
        app_id=app_data["app_id"],
        app_name=app_data["app_name"],
        launchpad_app_name=app_data["launchpad_app_name"],
        is_internal=app_data["is_internal"],
        is_shared=app_data["is_shared"],
        user_id=app_data["user_id"],
        url=app_data["url"],
        template_name=app_data["template_name"],
    )

    result = await insert_app(mock_db_session, **app_data)

    assert isinstance(result, InstalledApp)
    assert result.app_id == app_data["app_id"]
    assert result.app_name == app_data["app_name"]
    mock_db_session.execute.assert_called_once()


async def test_delete_app_success(mock_db_session: MagicMock, app_id: UUID) -> None:
    mock_app_instance = MagicMock(spec=InstalledApp)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
        mock_app_instance
    )
    mock_db_session.delete.return_value = None

    await delete_app(mock_db_session, app_id)

    mock_db_session.execute.assert_called_once()


async def test_delete_app_not_found(mock_db_session: MagicMock, app_id: UUID) -> None:
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    await delete_app(mock_db_session, app_id)
    mock_db_session.execute.assert_called_once()
    mock_db_session.delete.assert_not_called()
