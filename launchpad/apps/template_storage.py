import logging
import typing
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from launchpad.apps.registry.internal.embeddings import EmbeddingsApp
from launchpad.apps.registry.internal.llm_inference import LlmInferenceApp
from launchpad.apps.registry.internal.postgres import PostgresApp
from launchpad.apps.registry.shared.openwebui import OpenWebUIApp
from launchpad.apps.template_models import AppTemplate


logger = logging.getLogger(__name__)


async def seed_templates(db: AsyncSession) -> None:
    """
    Seed all app templates into the AppTemplate table.
    This includes both internal apps (vllm, postgres, embeddings) and user-facing apps (OpenWebUI).
    """

    logger.info("Seeding app templates")

    # Seed internal app templates
    for app_class, handler_name in [
        (LlmInferenceApp, "LlmInferenceApp"),
        (PostgresApp, "PostgresApp"),
        (EmbeddingsApp, "EmbeddingsApp"),
    ]:
        await insert_template(
            db=db,
            name=app_class.name,
            template_name=app_class.template_name,
            template_version=app_class.template_version,
            verbose_name=app_class.verbose_name,
            description_short=app_class.description_short,
            description_long=app_class.description_long,
            logo=app_class.logo,
            documentation_urls=app_class.documentation_urls,
            external_urls=app_class.external_urls,
            tags=app_class.tags,
            is_internal=app_class.is_internal,
            is_shared=app_class.is_shared,
            handler_class=handler_name,
        )
        logger.info(f"Seeded internal template: {app_class.name}")

    # Seed user-facing templates (OpenWebUI)
    openwebui = OpenWebUIApp
    await insert_template(
        db=db,
        name=openwebui.name,
        template_name=openwebui.template_name,
        template_version=openwebui.template_version,
        verbose_name=openwebui.verbose_name,
        description_short=openwebui.description_short,
        description_long=openwebui.description_long,
        logo=openwebui.logo,
        documentation_urls=openwebui.documentation_urls,
        external_urls=openwebui.external_urls,
        tags=openwebui.tags,
        is_internal=openwebui.is_internal,
        is_shared=openwebui.is_shared,
        handler_class="OpenWebUIApp",
    )
    logger.info(f"Seeded user-facing template: {openwebui.name}")

    logger.info("Template seeding complete")


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
    """
    Insert or update a template.

    Note: default_inputs is currently optional for backwards compatibility,
    but will be converted to an empty dict if None.
    """
    # Ensure default_inputs is never None
    if default_inputs is None:
        default_inputs = {}
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
    logger.info(f"list_templates called with is_internal={is_internal}")

    where = []
    if is_internal is not None:
        where.append(AppTemplate.is_internal.is_(is_internal))

    query = select(AppTemplate)
    if where:
        query = query.where(and_(*where))

    logger.info(f"Executing query: {query}")
    cursor = await db.execute(query)
    results = cursor.scalars().all()
    logger.info(f"Found {len(results)} templates")
    for template in results:
        logger.info(
            f"  - {template.name}: {template.verbose_name} "
            f"(is_internal={template.is_internal}, is_shared={template.is_shared})"
        )

    return results
