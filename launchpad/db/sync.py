from pathlib import Path

from alembic import command
from alembic.config import Config


def sync_db(dsn: str) -> None:
    alembic_cfg = Config()
    script_location = str(Path(__file__).parent.parent.parent / "alembic")
    alembic_cfg.set_main_option("script_location", script_location)
    alembic_cfg.set_main_option("sqlalchemy.url", dsn)
    command.upgrade(alembic_cfg, "head")
