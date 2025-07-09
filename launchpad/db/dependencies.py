from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request


async def get_db(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    """
    Yields a session from the session-pool.
    """
    async with request.app.db() as db:
        yield db


Db = Annotated[AsyncSession, Depends(get_db)]
