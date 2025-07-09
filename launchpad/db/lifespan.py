import logging
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from launchpad.app import App
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_db(app: App) -> AsyncIterator[None]:
    logger.info("creating db engine")

    app.db_engine = create_async_engine(
        app.config.postgres.dsn,
        future=True,
        pool_pre_ping=True,
        pool_size=app.config.postgres.pool_min_size,
        pool_recycle=3600,
        max_overflow=max(
            0, app.config.postgres.pool_max_size - app.config.postgres.pool_min_size
        ),
        pool_timeout=app.config.postgres.connect_timeout_s,
    )

    app.db = async_sessionmaker(app.db_engine, expire_on_commit=False)
    logger.info("db engine created")

    try:
        yield
    finally:
        logger.info("closing db engine")
        await app.db_engine.dispose()
        logger.info("db engine closed")
