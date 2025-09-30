import typing
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from launchpad.apps.template_models import AppTemplate


async def select_template(
    db: AsyncSession,
    id: UUID | None = None,
    name: str | None = None,
    is_internal: bool | None = None,
) -> AppTemplate | None:
    where = []
    if id is not None:
        where.append(AppTemplate.id == id)
    if name is not None:
        where.append(AppTemplate.name == name)
    if is_internal is not None:
        where.append(AppTemplate.is_internal.is_(is_internal))

    query = select(AppTemplate).where(and_(*where))
    cursor = await db.execute(query)
    return cursor.scalar_one_or_none()


async def insert_template(
    db: AsyncSession,
    name: str,
    template_name: str,
    template_version: str,
    verbose_name: str,
    description_short: str,
    description_long: str,
    logo: str,
    documentation_urls: list[dict[str, str]],
    external_urls: list[dict[str, str]],
    tags: list[str],
    is_internal: bool,
    is_shared: bool,
    handler_class: str | None = None,
    default_inputs: dict[str, Any] | None = None,
) -> AppTemplate:
    """Insert or update a template"""
    query = (
        insert(AppTemplate)
        .values(
            dict(
                id=uuid4(),
                name=name,
                template_name=template_name,
                template_version=template_version,
                verbose_name=verbose_name,
                description_short=description_short,
                description_long=description_long,
                logo=logo,
                documentation_urls=documentation_urls,
                external_urls=external_urls,
                tags=tags,
                is_internal=is_internal,
                is_shared=is_shared,
                handler_class=handler_class,
                default_inputs=default_inputs,
            )
        )
        .on_conflict_do_update(
            constraint="unique__app_templates__name",
            set_=dict(
                template_name=template_name,
                template_version=template_version,
                verbose_name=verbose_name,
                description_short=description_short,
                description_long=description_long,
                logo=logo,
                documentation_urls=documentation_urls,
                external_urls=external_urls,
                tags=tags,
                is_internal=is_internal,
                is_shared=is_shared,
                handler_class=handler_class,
                default_inputs=default_inputs,
            ),
        )
        .returning(AppTemplate)
    )
    cursor = await db.execute(query)
    template = cursor.scalar()
    return typing.cast(AppTemplate, template)


async def delete_template(
    db: AsyncSession,
    template_id: UUID,
) -> None:
    await db.execute(delete(AppTemplate).where(AppTemplate.id == template_id))


async def list_templates(
    db: AsyncSession,
    is_internal: bool | None = None,
) -> typing.Sequence[AppTemplate]:
    where = []
    if is_internal is not None:
        where.append(AppTemplate.is_internal.is_(is_internal))

    query = select(AppTemplate)
    if where:
        query = query.where(and_(*where))
    cursor = await db.execute(query)
    return cursor.scalars().all()
