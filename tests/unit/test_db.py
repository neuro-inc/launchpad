from typing import Any
from unittest.mock import MagicMock, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

from launchpad.app import Launchpad
from launchpad.db.base import DSN, POSTGRES_DSN_SCHEMA, POSTGRES_ASYNCPG_DSN_SCHEMA
from launchpad.db.dependencies import get_db


@pytest.fixture
def mock_db_session_maker() -> MagicMock:
    mock_maker = MagicMock(spec=async_sessionmaker)
    mock_session = AsyncMock(spec=AsyncSession)

    # Create a mock context manager for the session maker
    mock_session_context_manager = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session

    # When __aexit__ is called on the context manager, ensure session.close() is called
    async def mock_aexit(*args: Any, **kwargs: Any) -> None:
        await mock_session.close()

    mock_session_context_manager.__aexit__.side_effect = mock_aexit

    mock_maker.return_value = mock_session_context_manager
    return mock_maker


@pytest.fixture
def mock_launchpad_app(mock_db_session_maker: MagicMock) -> MagicMock:
    app = MagicMock(spec=Launchpad)
    app.db = mock_db_session_maker
    return app


@pytest.fixture
def mock_request(mock_launchpad_app: MagicMock) -> MagicMock:
    request = MagicMock(spec=Request)
    request.app = mock_launchpad_app
    return request


def test_dsn_with_plain_schema_asyncpg_to_plain() -> None:
    dsn = f"{POSTGRES_ASYNCPG_DSN_SCHEMA}://user:pass@host:port/db"
    expected_dsn = f"{POSTGRES_DSN_SCHEMA}://user:pass@host:port/db"
    assert DSN.with_plain_schema(dsn) == expected_dsn


def test_dsn_with_plain_schema_plain_to_plain() -> None:
    dsn = f"{POSTGRES_DSN_SCHEMA}://user:pass@host:port/db"
    expected_dsn = f"{POSTGRES_DSN_SCHEMA}://user:pass@host:port/db"
    assert DSN.with_plain_schema(dsn) == expected_dsn


def test_dsn_with_asyncpg_schema_plain_to_asyncpg() -> None:
    dsn = f"{POSTGRES_DSN_SCHEMA}://user:pass@host:port/db"
    expected_dsn = f"{POSTGRES_ASYNCPG_DSN_SCHEMA}://user:pass@host:port/db"
    assert DSN.with_asyncpg_schema(dsn) == expected_dsn


def test_dsn_with_asyncpg_schema_asyncpg_to_asyncpg() -> None:
    dsn = f"{POSTGRES_ASYNCPG_DSN_SCHEMA}://user:pass@host:port/db"
    expected_dsn = f"{POSTGRES_ASYNCPG_DSN_SCHEMA}://user:pass@host:port/db"
    assert DSN.with_asyncpg_schema(dsn) == expected_dsn


async def test_get_db_session(
    mock_request: MagicMock, mock_db_session_maker: MagicMock
) -> None:
    # Get the async generator object
    async for session in get_db(mock_request):
        assert isinstance(session, AsyncMock)  # It should be our mocked session
        mock_db_session_maker.assert_called_once()  # Ensure the session maker was called

    session.close.assert_called_once()  # type: ignore[attr-defined]
