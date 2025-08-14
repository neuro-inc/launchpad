from __future__ import annotations

import json
import os
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from yarl import URL

from launchpad.db.base import DSN

APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class KeycloakConfig:
    url: URL
    realm: str
    client_id: str = "frontend"


@dataclass
class ApoloConfig:
    cluster: str
    org_name: str
    project_name: str
    apps_api_url: str
    token: str
    self_domain: str
    base_domain: str
    auth_middleware_name: str


@dataclass
class AppsConfig:
    vllm: dict[str, Any]
    postgres: dict[str, Any]
    embeddings: dict[str, Any]


@dataclass
class PostgresConfig:
    dsn: str

    pool_min_size: int = 10
    pool_max_size: int = 10

    connect_timeout_s: float = 60.0
    command_timeout_s: float = 60.0


@dataclass(frozen=True)
class Config:
    postgres: PostgresConfig
    keycloak: KeycloakConfig
    apolo: ApoloConfig
    apps: AppsConfig
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
            keycloak=self.create_keycloak(),
            apolo=self.create_apolo(),
            apps=self.create_apps(),
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
        return PostgresConfig(dsn=dsn)

    def create_keycloak(self) -> KeycloakConfig:
        return KeycloakConfig(
            url=URL(f"https://{self._environ['KEYCLOAK_URL']}"),
            realm=self._environ["KEYCLOAK_REALM"],
        )

    def create_apolo(self) -> ApoloConfig:
        passed_config = os.environ["APOLO_PASSED_CONFIG"]
        parsed_config = json.loads(b64decode(passed_config))
        return ApoloConfig(
            cluster=parsed_config["cluster"],
            org_name=parsed_config["org_name"],
            project_name=parsed_config["project_name"],
            apps_api_url=parsed_config["url"],
            token=parsed_config["token"],
            self_domain=self._environ["SELF_DOMAIN"],
            base_domain=self._environ["BASE_DOMAIN"],
            auth_middleware_name=self._environ["AUTH_MIDDLEWARE_NAME"],
        )

    def create_apps(self) -> AppsConfig:
        initial_config = json.loads(os.environ["LAUNCHPAD_INITIAL_CONFIG"])
        return AppsConfig(
            vllm=initial_config["vllm"],
            postgres=initial_config["postgres"],
            embeddings=initial_config["text-embeddings"],
        )
