import logging
import typing
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from launchpad.apps.models import (
    UNIQUE__INSTALLED_APPS__LAUNCHPAD_APP_NAME__USER_ID,
    InstalledApp,
)


logger = logging.getLogger(__name__)


async def select_app(
    db: AsyncSession,
    id: UUID | None = None,
    name: str | None = None,
    is_internal: bool | None = None,
    is_shared: bool | None = None,
    user_id: str | None = None,
    url: str | None = None,
) -> InstalledApp | None:
    where = []
    if id is not None:
        where.append(InstalledApp.app_id == id)
    if name is not None:
        where.append(InstalledApp.launchpad_app_name == name)
    if is_internal is not None:
        where.append(InstalledApp.is_internal.is_(is_internal))
    if is_shared is not None:
        where.append(InstalledApp.is_shared.is_(is_shared))
    if user_id is not None:
        where.append(InstalledApp.user_id == user_id)
    if url is not None:
        where.append(InstalledApp.url == url)

    query = select(InstalledApp).where(and_(*where))
    cursor = await db.execute(query)
    return cursor.scalar_one_or_none()


async def select_app_by_any_url(
    db: AsyncSession,
    url: str,
) -> InstalledApp | None:
    """
    Find an installed app by checking both the main URL and external_url_list.

    This is useful for authorization where a request might come to any of the app's endpoints.

    Args:
        db: Database session
        url: The URL to search for

    Returns:
        The installed app if found by main URL or any external URL, None otherwise
    """
    from sqlalchemy import any_, or_

    # Search for app where url matches either the main url field OR is in external_url_list
    # Using PostgreSQL's = ANY(array) syntax via SQLAlchemy's any_ function
    query = select(InstalledApp).where(
        or_(
            InstalledApp.url == url,
            url == any_(InstalledApp.external_url_list),  # type: ignore[arg-type]
        )
    )
    cursor = await db.execute(query)
    return cursor.scalar_one_or_none()


async def insert_app(
    db: AsyncSession,
    app_id: UUID,
    app_name: str,
    launchpad_app_name: str,
    is_internal: bool,
    is_shared: bool,
    user_id: str | None,
    url: str | None,
    template_name: str,
    external_url_list: list[str] | None = None,
) -> InstalledApp:
    query = (
        insert(InstalledApp)
        .values(
            dict(
                id=uuid4(),
                app_id=app_id,
                app_name=app_name,
                launchpad_app_name=launchpad_app_name,
                is_internal=is_internal,
                is_shared=is_shared,
                user_id=user_id,
                url=url,
                template_name=template_name,
                external_url_list=external_url_list or [],
            )
        )
        # possible update a URL of an app
        .on_conflict_do_update(
            constraint=UNIQUE__INSTALLED_APPS__LAUNCHPAD_APP_NAME__USER_ID,
            set_=dict(
                app_id=app_id,
                app_name=app_name,
                url=url,
                external_url_list=external_url_list or [],
            ),
        )
        .returning(InstalledApp)
    )
    cursor = await db.execute(query)
    installed_app = cursor.scalar()
    return typing.cast(InstalledApp, installed_app)


async def update_app_url(
    db: AsyncSession,
    app_id: UUID,
    url: str,
) -> InstalledApp | None:
    """Update the URL of an installed app"""

    query = (
        update(InstalledApp)
        .where(InstalledApp.app_id == app_id)
        .values(url=url)
        .returning(InstalledApp)
    )
    cursor = await db.execute(query)
    return cursor.scalar_one_or_none()


async def update_app_endpoints(
    db: AsyncSession,
    app_id: UUID,
    url: str | None,
    external_url_list: list[str],
) -> InstalledApp | None:
    """Update the URL and external_url_list of an installed app"""

    query = (
        update(InstalledApp)
        .where(InstalledApp.app_id == app_id)
        .values(url=url, external_url_list=external_url_list)
        .returning(InstalledApp)
    )
    cursor = await db.execute(query)
    return cursor.scalar_one_or_none()


async def delete_app(
    db: AsyncSession,
    app_id: UUID,
) -> None:
    await db.execute(delete(InstalledApp).where(InstalledApp.app_id == app_id))


async def list_apps(
    db: AsyncSession,
    user_id: str | None = None,
    is_internal: bool | None = None,
    is_shared: bool | None = None,
    template_name: str | None = None,
) -> typing.Sequence[InstalledApp]:
    logger.debug(
        f"list_apps called with filters: user_id={user_id}, "
        f"is_internal={is_internal}, is_shared={is_shared}, template_name={template_name}"
    )

    where = []
    if user_id is not None:
        where.append(InstalledApp.user_id == user_id)
    if is_internal is not None:
        where.append(InstalledApp.is_internal.is_(is_internal))
    if is_shared is not None:
        where.append(InstalledApp.is_shared.is_(is_shared))
    if template_name is not None:
        where.append(InstalledApp.template_name == template_name)

    query = select(InstalledApp)
    if where:
        query = query.where(and_(*where))

    logger.debug(f"Executing query: {query}")
    cursor = await db.execute(query)
    results = cursor.scalars().all()
    logger.debug(f"Query returned {len(results)} results")

    return results
