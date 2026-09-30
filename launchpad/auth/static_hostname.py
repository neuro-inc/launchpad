import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

from launchpad.auth.models import AliasSession
from launchpad.errors import Forbidden
from launchpad.hostnames import canonical_authority


if TYPE_CHECKING:
    from launchpad.app import Launchpad


LOGIN_TTL_SECONDS = 300


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class StaticHostnameAuthService:
    def __init__(self, db: async_sessionmaker[AsyncSession], launchpad_id: UUID):
        self._db = db
        self._launchpad_id = launchpad_id
        self.nonce_cookie = f"__Host-launchpad-{launchpad_id.hex}-nonce"
        self.session_cookie = f"__Host-launchpad-{launchpad_id.hex}-session"
        self.callback_path = f"/_apolo/launchpad/{launchpad_id.hex}/handoff"

    async def begin(self, hostname: str, app_id: UUID) -> tuple[str, str]:
        hostname = canonical_authority(hostname)
        login, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        async with self._db() as db, db.begin():
            await db.execute(delete(AliasSession).where(AliasSession.expires_at <= now))
            db.add(
                AliasSession(
                    launchpad_id=self._launchpad_id,
                    app_id=app_id,
                    hostname=hostname,
                    login_digest=_digest(login),
                    nonce_digest=_digest(nonce),
                    expires_at=now + timedelta(seconds=LOGIN_TTL_SECONDS),
                )
            )
        return login, nonce

    async def read_login(self, login: str) -> AliasSession:
        async with self._db() as db:
            record = await db.scalar(
                select(AliasSession).where(
                    AliasSession.launchpad_id == self._launchpad_id,
                    AliasSession.login_digest == _digest(login),
                    AliasSession.access_token.is_(None),
                    AliasSession.expires_at > datetime.now(UTC),
                )
            )
        if record is None:
            raise Forbidden()
        return record

    async def issue(
        self, login: str, token: str, token_expires_at: datetime, user_id: str
    ) -> str:
        grant = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        async with self._db() as db, db.begin():
            record_id = await db.scalar(
                update(AliasSession)
                .where(
                    AliasSession.launchpad_id == self._launchpad_id,
                    AliasSession.login_digest == _digest(login),
                    AliasSession.access_token.is_(None),
                    AliasSession.expires_at > now,
                )
                .values(
                    grant_digest=_digest(grant),
                    access_token=token,
                    token_expires_at=token_expires_at,
                    user_id=user_id,
                    expires_at=min(token_expires_at, now + timedelta(minutes=1)),
                )
                .returning(AliasSession.id)
            )
        if record_id is None:
            raise Forbidden()
        return grant

    async def redeem(self, grant: str, nonce: str, hostname: str, app_id: UUID) -> str:
        hostname = canonical_authority(hostname)
        session = secrets.token_urlsafe(32)
        async with self._db() as db, db.begin():
            record_id = await db.scalar(
                update(AliasSession)
                .where(
                    AliasSession.launchpad_id == self._launchpad_id,
                    AliasSession.grant_digest == _digest(grant),
                    AliasSession.nonce_digest == _digest(nonce),
                    AliasSession.hostname == hostname,
                    AliasSession.app_id == app_id,
                    AliasSession.expires_at > datetime.now(UTC),
                )
                .values(
                    grant_digest=None,
                    session_digest=_digest(session),
                    expires_at=AliasSession.token_expires_at,
                )
                .returning(AliasSession.id)
            )
        if record_id is None:
            raise Forbidden()
        return session

    async def get_token(self, session: str, hostname: str, app_id: UUID) -> str | None:
        if not session:
            return None
        hostname = canonical_authority(hostname)
        async with self._db() as db:
            return await db.scalar(
                select(AliasSession.access_token).where(
                    AliasSession.launchpad_id == self._launchpad_id,
                    AliasSession.session_digest == _digest(session),
                    AliasSession.hostname == hostname,
                    AliasSession.app_id == app_id,
                    AliasSession.expires_at > datetime.now(UTC),
                )
            )

    async def revoke_user(self, user_id: str) -> None:
        async with self._db() as db, db.begin():
            await db.execute(
                delete(AliasSession).where(
                    AliasSession.launchpad_id == self._launchpad_id,
                    AliasSession.user_id == user_id,
                )
            )


async def dep_static_hostname_auth(request: Request) -> StaticHostnameAuthService:
    app: "Launchpad" = request.app
    return app.static_hostname_auth


DepStaticHostnameAuth = Annotated[
    StaticHostnameAuthService, Depends(dep_static_hostname_auth)
]
