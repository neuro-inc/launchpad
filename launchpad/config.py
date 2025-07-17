from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config as AlembicConfig
from dotenv import load_dotenv

from launchpad.db.base import DSN

APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class PostgresConfig:
    dsn: str

    alembic: AlembicConfig
    run_migrations: bool = False

    # based on defaults
    # https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.connect
    pool_min_size: int = 10
    pool_max_size: int = 10

    connect_timeout_s: float = 60.0
    command_timeout_s: float = 60.0


@dataclass(frozen=True)
class Config:
    postgres: PostgresConfig
    server: ServerConfig = ServerConfig()


class EnvironConfigFactory:
    def __init__(self, environ: dict[str, str] | None = None) -> None:
        if environ is None:
            # load a .env file for local development
            load_dotenv(dotenv_path=ROOT_DIR / ".env")
            self._environ: dict[str, str] = dict(os.environ)
        else:
            self._environ = environ

    def create(self) -> Config:
        return Config(
            server=self.create_server(),
            postgres=self.create_postgres(),
        )

    def create_server(self) -> ServerConfig:
        return ServerConfig(
            host=self._environ.get("HOST", ServerConfig.host),
            port=int(self._environ.get("PORT", ServerConfig.port)),
        )

    def create_postgres(self) -> PostgresConfig:
        db_host = self._environ["DB_HOST"]
        db_user = self._environ["DB_USER"]
        db_password = self._environ["DB_PASSWORD"]
        db_name = self._environ["DB_NAME"]
        db_port = self._environ.get("DB_PORT", 5432)
        postgres_dsn = (
            f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        dsn = DSN.with_asyncpg_schema(postgres_dsn)
        return PostgresConfig(dsn=dsn, alembic=self.create_alembic(postgres_dsn))

    def create_alembic(self, postgres_dsn: str) -> AlembicConfig:
        parent_path = pathlib.Path(__file__).resolve().parent.parent
        ini_path = str(parent_path / "alembic.ini")
        script_path = str(parent_path / "alembic")
        config = AlembicConfig(ini_path)
        config.set_main_option("script_location", script_path)
        config.set_main_option("sqlalchemy.url", postgres_dsn.replace("%", "%%"))
        return config
