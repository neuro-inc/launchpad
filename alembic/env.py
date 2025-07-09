import asyncio
import sys

from neuro_logging import init_logging
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
from alembic.script import ScriptDirectory
from launchpad.config import EnvironConfigFactory
from launchpad.db.base import DSN, Base


config = context.config


if sys.argv[0].endswith("alembic"):
    init_logging()


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    update_config_with_plain_schema()
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    def process_revision_directives(context, revision, directives):
        """
        Adds a leading incremental number of the migration, e.g.:
        0001, 0002, etc.
        """
        migration_script = directives[0]
        head_revision = ScriptDirectory.from_config(context.config).get_current_head()
        if head_revision is None:
            new_rev_id = 1
        else:
            last_rev_id = int(head_revision.lstrip("0"))
            new_rev_id = last_rev_id + 1

        # fill zeros
        migration_script.rev_id = f"{new_rev_id:04}"

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        connection.execute(text("SELECT pg_advisory_xact_lock(10000)"))
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    update_config_with_asyncpg_schema()
    connectable = AsyncEngine(
        engine_from_config(  # type: ignore
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def update_config_with_asyncpg_schema():
    sqlalchemy_url = config.get_main_option("sqlalchemy.url")
    if not sqlalchemy_url:
        db_config = EnvironConfigFactory().create_postgres()
        config.set_main_option("sqlalchemy.url", db_config.dsn)


def update_config_with_plain_schema() -> None:
    if config.get_main_option("sqlalchemy.url"):
        return

    db_config = EnvironConfigFactory().create_postgres()
    postgres_dsn = DSN.with_plain_schema(db_config.dsn)
    config.set_main_option("sqlalchemy.url", postgres_dsn)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
