import datetime
import enum

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid import UUID, uuid4
from sqlalchemy.orm import MappedAsDataclass

from sqlalchemy import UUID as SQL_UUID, Enum as SQL_ENUM

POSTGRES_DSN_SCHEMA = "postgresql"
POSTGRES_ASYNCPG_DSN_SCHEMA = "postgresql+asyncpg"


class DSN:
    @staticmethod
    def with_plain_schema(dsn: str) -> str:
        if dsn.startswith(POSTGRES_ASYNCPG_DSN_SCHEMA + "://"):
            dsn = POSTGRES_DSN_SCHEMA + dsn[len(POSTGRES_ASYNCPG_DSN_SCHEMA) :]
        return dsn

    @staticmethod
    def with_asyncpg_schema(dsn: str) -> str:
        if dsn.startswith(POSTGRES_DSN_SCHEMA + "://"):
            dsn = POSTGRES_ASYNCPG_DSN_SCHEMA + dsn[len(POSTGRES_DSN_SCHEMA) :]
        return dsn


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    """
    Abstract base class for all database models
    """

    __abstract__ = True

    type_annotation_map = {
        UUID: SQL_UUID,
        datetime.datetime: TIMESTAMP(timezone=True),
        enum.Enum: SQL_ENUM(enum.Enum, native_enum=True, inherit_schema=True),
    }

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    created_at: Mapped[datetime.datetime] = mapped_column(
        init=False, server_default=func.clock_timestamp()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        init=False,
        server_default=func.clock_timestamp(),
        server_onupdate=func.clock_timestamp(),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )
