import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

import pytest
from aiohttp import ClientSession
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request
from starlette.responses import Response
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config as AlembicConfig
from launchpad.api import root_router
from launchpad.app import Launchpad
from launchpad.apps.models import InstalledApp
from launchpad.apps.service import AppService, dep_app_service
from launchpad.auth import HEADER_X_FORWARDED_HOST, HEADER_X_FORWARDED_URI
from launchpad.auth.api import view_post_authorize
from launchpad.auth.models import AliasSession
from launchpad.auth.oauth import Oauth, dep_oauth
from launchpad.auth.static_hostname import (
    StaticHostnameAuthService,
    dep_static_hostname_auth,
)
from launchpad.config import Config
from launchpad.errors import Forbidden


@pytest.fixture
async def service(
    postgres_container: PostgresContainer, setup_database: str
) -> AsyncIterator[StaticHostnameAuthService]:
    engine = create_async_engine(
        postgres_container.get_connection_url(driver=None).replace(
            "postgresql://", "postgresql+asyncpg://"
        ),
        poolclass=NullPool,
    )
    yield StaticHostnameAuthService(
        async_sessionmaker(engine, expire_on_commit=False), uuid4()
    )
    await engine.dispose()


async def test_nonce_bound_grant_is_single_use(
    service: StaticHostnameAuthService,
) -> None:
    app_id, hostname = uuid4(), "silverfin-dev.apps.apolo.us"
    login, nonce = await service.begin(hostname, app_id)
    record = await service.read_login(login)
    assert record.app_id == app_id
    assert record.login_digest != login and record.nonce_digest != nonce
    grant = await service.issue(
        login,
        "server-token",
        datetime.now(UTC) + timedelta(hours=1),
        "owner@example.test",
    )
    with pytest.raises(Forbidden):
        await service.issue(
            login,
            "second-token",
            datetime.now(UTC) + timedelta(hours=1),
            "owner@example.test",
        )
    for wrong_nonce, wrong_host, wrong_app in [
        ("wrong", hostname, app_id),
        (nonce, "other.apps.apolo.us", app_id),
        (nonce, hostname, uuid4()),
    ]:
        with pytest.raises(Forbidden):
            await service.redeem(grant, wrong_nonce, wrong_host, wrong_app)
    session = await service.redeem(grant, nonce, hostname, app_id)
    with pytest.raises(Forbidden):
        await service.redeem(grant, nonce, hostname, app_id)
    assert session != "server-token"
    assert await service.get_token(session, hostname, app_id) == "server-token"
    assert await service.get_token(session, hostname, uuid4()) is None
    assert await service.get_token(session, "other.apps.apolo.us", app_id) is None


@pytest.mark.parametrize("stage", ["login", "grant", "session"])
async def test_expired_records_fail_closed(
    service: StaticHostnameAuthService, stage: str
) -> None:
    app_id, hostname = uuid4(), "expired.apps.apolo.us"
    login, nonce = await service.begin(hostname, app_id)
    grant = ""
    session = ""
    if stage != "login":
        grant = await service.issue(
            login, "token", datetime.now(UTC) + timedelta(hours=1), "owner@example.test"
        )
    if stage == "session":
        session = await service.redeem(grant, nonce, hostname, app_id)
    async with service._db() as db, db.begin():
        await db.execute(
            update(AliasSession)
            .where(AliasSession.hostname == hostname)
            .values(
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
    if stage == "login":
        with pytest.raises(Forbidden):
            await service.read_login(login)
    elif stage == "grant":
        with pytest.raises(Forbidden):
            await service.redeem(grant, nonce, hostname, app_id)
    else:
        assert await service.get_token(session, hostname, app_id) is None
    await service.begin("fresh.apps.apolo.us", uuid4())
    async with service._db() as db:
        assert (
            await db.scalar(
                select(AliasSession).where(AliasSession.hostname == hostname)
            )
            is None
        )


async def test_other_launchpad_cannot_use_grant_or_session(
    service: StaticHostnameAuthService,
) -> None:
    app_id, hostname = uuid4(), "silverfin-dev.apps.apolo.us"
    login, nonce = await service.begin(hostname, app_id)
    grant = await service.issue(
        login, "token", datetime.now(UTC) + timedelta(hours=1), "owner@example.test"
    )
    other = StaticHostnameAuthService(service._db, uuid4())
    with pytest.raises(Forbidden):
        await other.read_login(login)
    with pytest.raises(Forbidden):
        await other.redeem(grant, nonce, hostname, app_id)
    session = await service.redeem(grant, nonce, hostname, app_id)
    assert await other.get_token(session, hostname, app_id) is None


async def test_logout_revokes_all_user_grants_and_alias_sessions(
    service: StaticHostnameAuthService,
) -> None:
    app_id, hostname = uuid4(), "logout.apps.apolo.us"
    login, nonce = await service.begin(hostname, app_id)
    grant = await service.issue(
        login, "old-token", datetime.now(UTC) + timedelta(hours=1), "owner@example.test"
    )
    session = await service.redeem(grant, nonce, hostname, app_id)
    second_login, second_nonce = await service.begin(hostname, app_id)
    second_grant = await service.issue(
        second_login,
        "new-token",
        datetime.now(UTC) + timedelta(hours=1),
        "owner@example.test",
    )
    await service.revoke_user("other@example.test")
    assert await service.get_token(session, hostname, app_id) == "old-token"
    await service.revoke_user("owner@example.test")
    assert await service.get_token(session, hostname, app_id) is None
    with pytest.raises(Forbidden):
        await service.redeem(second_grant, second_nonce, hostname, app_id)


@pytest.mark.parametrize("trailing_dot", [False, True])
async def test_cross_domain_login_cookie_flow_and_logout(
    service: StaticHostnameAuthService,
    mock_config_auth: Config,
    trailing_dot: bool,
) -> None:
    alias = "silverfin-dev.apps.apolo.us"
    central = "launchpad.apps.imdc.org.apolo.us"
    app = Launchpad()
    app.config = mock_config_auth
    app.http = MagicMock(spec=ClientSession)
    oauth = Oauth(
        app.http, app.config.keycloak, "apps.imdc.org.apolo.us", central, uuid4()
    )
    installed = InstalledApp(
        app_id=uuid4(),
        app_name="silverfin",
        launchpad_app_name="silverfin",
        is_internal=False,
        is_shared=False,
        user_id="owner@example.test",
        url=None,
        template_name="service-deployment",
        external_url_list=[],
    )
    apps = MagicMock(spec=AppService)
    apps.resolve_app_for_authorization = AsyncMock(return_value=installed)
    app.dependency_overrides[dep_app_service] = lambda: apps
    app.dependency_overrides[dep_static_hostname_auth] = lambda: service
    app.dependency_overrides[dep_oauth] = lambda: oauth
    app.include_router(root_router)

    @app.get("/{path:path}")
    async def proxy_to_forward_auth(request: Request) -> Response:
        request.scope["headers"].extend(
            [
                (HEADER_X_FORWARDED_HOST.lower().encode(), request.url.netloc.encode()),
                (
                    HEADER_X_FORWARDED_URI.lower().encode(),
                    str(
                        request.url.path
                        + ("?" + request.url.query if request.url.query else "")
                    ).encode(),
                ),
            ]
        )
        return await view_post_authorize(request, apps, oauth, service)

    decoded = {
        "email": "owner@example.test",
        "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
    }
    with (
        patch.object(oauth, "_fetch_token", new=AsyncMock(return_value="server-token")),
        patch(
            "launchpad.auth.dependencies.token_from_string",
            new=AsyncMock(return_value=decoded),
        ),
        patch(
            "launchpad.auth.static_hostname_api.token_from_string",
            new=AsyncMock(return_value=decoded),
        ),
        TestClient(app, base_url=f"https://{alias}", follow_redirects=False) as browser,
    ):
        first = browser.get(f"https://{alias}{'.' if trailing_dot else ''}/")
        if trailing_dot:
            assert first.headers["location"] == f"https://{alias}/"
            assert "set-cookie" not in first.headers
            first = browser.get(first.headers["location"])
        assert first.status_code == 307
        assert "Domain=" not in first.headers["set-cookie"]
        start = browser.get(first.headers["location"])
        assert service.nonce_cookie not in start.request.headers.get("cookie", "")
        params = parse_qs(urlsplit(start.headers["location"]).query)
        assert params["redirect_uri"] == [f"https://{central}/auth/callback"]
        callback = browser.get(
            f"https://{central}/auth/callback?"
            + urlencode({"code": "code", "state": params["state"][0]})
        )
        assert callback.status_code == 307
        finish = browser.get(callback.headers["location"])
        assert finish.status_code == 307
        assert "server-token" not in finish.headers["location"]
        redemption = browser.get(finish.headers["location"])
        assert redemption.status_code == 307
        assert "Domain=" not in redemption.headers.get_list("set-cookie")[0]
        authorized = browser.get(redemption.headers["location"])
        assert authorized.status_code == 200
        assert service.session_cookie in authorized.request.headers["cookie"]
        assert "server-token" not in authorized.request.headers["cookie"]
        assert browser.get(finish.headers["location"]).status_code == 403
        logout = browser.post(f"https://{central}/auth/logout")
        assert logout.status_code == 200
        assert browser.get(f"https://{alias}/").status_code == 307
        apps.resolve_app_for_authorization.return_value = None
        assert browser.get(f"https://{alias}/").status_code == 403


async def test_concurrent_grant_redemption_has_one_winner(
    service: StaticHostnameAuthService,
) -> None:
    app_id, hostname = uuid4(), "concurrent.apps.apolo.us"
    login, nonce = await service.begin(hostname, app_id)
    grant = await service.issue(
        login, "token", datetime.now(UTC) + timedelta(hours=1), "owner@example.test"
    )
    results = await asyncio.gather(
        service.redeem(grant, nonce, hostname, app_id),
        service.redeem(grant, nonce, hostname, app_id),
        return_exceptions=True,
    )
    assert sum(isinstance(result, str) for result in results) == 1
    assert sum(isinstance(result, Forbidden) for result in results) == 1


def test_alias_session_migration_upgrade_and_downgrade(
    postgres_container: PostgresContainer,
) -> None:
    database = "alias_migration_" + uuid4().hex
    source_url = make_url(postgres_container.get_connection_url(driver=None)).set(
        drivername="postgresql+psycopg2"
    )
    admin = create_engine(source_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    database_url = source_url.set(database=database)
    migration = AlembicConfig()
    migration.set_main_option(
        "script_location", str(Path(__file__).parents[2] / "alembic")
    )
    migration.set_main_option(
        "sqlalchemy.url",
        database_url.set(drivername="postgresql+asyncpg").render_as_string(
            hide_password=False
        ),
    )
    engine = create_engine(database_url)
    try:
        command.upgrade(migration, "head")
        columns = {
            column["name"]
            for column in inspect(engine).get_columns("auth_alias_sessions")
        }
        assert {
            "login_digest",
            "grant_digest",
            "session_digest",
            "user_id",
            "expires_at",
        } <= columns
        indexes = inspect(engine).get_indexes("auth_alias_sessions")
        assert any(
            index["name"] == "ix_auth_alias_sessions_launchpad_id_user_id"
            and index["column_names"] == ["launchpad_id", "user_id"]
            for index in indexes
        )
        command.downgrade(migration, "0006")
        assert not inspect(engine).has_table("auth_alias_sessions")
        command.upgrade(migration, "head")
        assert inspect(engine).has_table("auth_alias_sessions")
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}"'))
        admin.dispose()


async def test_session_binding_uses_canonical_hostname(
    service: StaticHostnameAuthService,
) -> None:
    app_id = uuid4()
    login, nonce = await service.begin("SILVERFIN.APPS.APOLO.US.:443", app_id)
    assert (await service.read_login(login)).hostname == "silverfin.apps.apolo.us"
    grant = await service.issue(
        login, "token", datetime.now(UTC) + timedelta(hours=1), "owner@example.test"
    )
    session = await service.redeem(grant, nonce, "silverfin.apps.apolo.us", app_id)
    assert (
        await service.get_token(session, "SILVERFIN.APPS.APOLO.US.:443", app_id)
        == "token"
    )
