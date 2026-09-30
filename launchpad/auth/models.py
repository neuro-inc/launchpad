import dataclasses
from datetime import datetime
from uuid import UUID

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from launchpad.db.base import Base


@dataclasses.dataclass
class User:
    id: str
    email: str
    name: str
    groups: list[str] = dataclasses.field(default_factory=list)


class AliasSession(Base):
    __tablename__ = "auth_alias_sessions"
    __table_args__ = (
        Index("ix_auth_alias_sessions_launchpad_id_user_id", "launchpad_id", "user_id"),
    )

    launchpad_id: Mapped[UUID]
    app_id: Mapped[UUID]
    hostname: Mapped[str]
    login_digest: Mapped[str] = mapped_column(unique=True)
    nonce_digest: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(index=True)
    grant_digest: Mapped[str | None] = mapped_column(unique=True, default=None)
    session_digest: Mapped[str | None] = mapped_column(unique=True, default=None)
    access_token: Mapped[str | None] = mapped_column(default=None)
    token_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    user_id: Mapped[str | None] = mapped_column(default=None)
