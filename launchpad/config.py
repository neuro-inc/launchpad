from __future__ import annotations

import json
import logging
import os
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from yarl import URL

from launchpad.db.base import DSN


logger = logging.getLogger(__name__)


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
class BrandingConfig:
    title: str | None = None
    background: str | None = None
    branding_dir: Path = Path("/etc/launchpad/branding")


@dataclass(frozen=True)
class Config:
    postgres: PostgresConfig
    keycloak: KeycloakConfig
    apolo: ApoloConfig
    branding: BrandingConfig
    apps: AppsConfig | None
    server: ServerConfig = ServerConfig()
    instance_id: UUID | None = None
    skip_seed_templates: bool = False


class EnvironConfigFactory:
    def __init__(self, environ: dict[str, str] | None = None) -> None:
        if environ is None:
            # load a .env file for local development
            load_dotenv(dotenv_path=ROOT_DIR / ".env")
            self._environ: dict[str, str] = dict(os.environ)
        else:
            self._environ = environ

    def create(self) -> Config:
        try:
            return Config(
                server=self.create_server(),
                keycloak=self.create_keycloak(),
                apolo=self.create_apolo(),
                apps=self.create_apps(),
                postgres=self.create_postgres(),
                instance_id=self.get_instance_id(),
                skip_seed_templates=bool(
                    self._environ.get("LAUNCHPAD_SKIP_SEED_TEMPLATES")
                ),
                branding=self.create_branding(),
            )
        except KeyError as e:
            logger.exception("Missing required environment variable: %s", e)
            raise
        except Exception as e:
            logger.exception("Failed to create configuration: %s", e)
            raise

    def get_instance_id(self) -> UUID | None:
        instance_id = self._environ.get("LAUNCHPAD_APP_ID")
        if instance_id is None:
            return None
        try:
            return UUID(instance_id)
        except ValueError as e:
            logger.exception(
                "Invalid UUID format for LAUNCHPAD_APP_ID: %s", instance_id
            )
            raise

    def create_server(self) -> ServerConfig:
        return ServerConfig(
            host=self._environ.get("HOST", ServerConfig.host),
            port=int(self._environ.get("PORT", ServerConfig.port)),
        )

    def create_postgres(self) -> PostgresConfig:
        try:
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
        except KeyError as e:
            logger.exception("Missing required database environment variable: %s", e)
            raise

    def create_keycloak(self) -> KeycloakConfig:
        try:
            return KeycloakConfig(
                url=URL(f"https://{self._environ['KEYCLOAK_URL']}"),
                realm=self._environ["KEYCLOAK_REALM"],
            )
        except KeyError as e:
            logger.exception("Missing required Keycloak environment variable: %s", e)
            raise

    def create_apolo(self) -> ApoloConfig:
        try:
            passed_config = self._environ["APOLO_PASSED_CONFIG"]
            parsed_config = json.loads(b64decode(passed_config))
            url = URL(parsed_config["url"])
            apps_api_url = f"{url.scheme}://{url.host}/apis/apps"
            return ApoloConfig(
                cluster=parsed_config["cluster"],
                org_name=parsed_config["org_name"],
                project_name=parsed_config["project_name"],
                apps_api_url=apps_api_url,
                token=parsed_config["token"],
                self_domain=self._environ["SELF_DOMAIN"],
                base_domain=self._environ["BASE_DOMAIN"],
                auth_middleware_name=self._environ["AUTH_MIDDLEWARE_NAME"],
            )
        except KeyError as e:
            logger.exception(
                "Missing required Apolo environment variable or config key: %s", e
            )
            raise
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse APOLO_PASSED_CONFIG as JSON: %s", e)
            raise
        except Exception as e:
            logger.exception("Failed to create Apolo configuration: %s", e)
            raise

    def create_apps(self) -> AppsConfig | None:
        initial_config_str = (
            self._environ.get("LAUNCHPAD_INITIAL_CONFIG") or ""
        ).strip()

        # Check if config is empty, just whitespace, or Go's empty map representation
        if not initial_config_str or initial_config_str in ("{}", "map[]"):
            # No quickstart config provided, return None to skip internal apps installation
            logger.debug(
                "No LAUNCHPAD_INITIAL_CONFIG provided, skipping apps installation"
            )
            return None

        # Try to parse JSON, return None if invalid
        try:
            initial_config = json.loads(initial_config_str)
        except (json.JSONDecodeError, ValueError) as e:
            # Invalid JSON (including Go's "map[]"), treat as no config
            logger.warning("Failed to parse LAUNCHPAD_INITIAL_CONFIG as JSON: %s", e)
            return None

        # Validate that required keys are present
        required_keys = ["vllm", "postgres", "text-embeddings"]
        if not all(key in initial_config for key in required_keys):
            # Config is incomplete, return None
            logger.warning(
                "LAUNCHPAD_INITIAL_CONFIG missing required keys. Expected: %s, Got: %s",
                required_keys,
                list(initial_config.keys()),
            )
            return None

        return AppsConfig(
            vllm=initial_config["vllm"],
            postgres=initial_config["postgres"],
            embeddings=initial_config["text-embeddings"],
        )

    def create_branding(self) -> BrandingConfig:
        branding_dir = self._environ.get("BRANDING_DIR", "/etc/launchpad/branding")
        return BrandingConfig(
            title=self._environ.get("BRANDING_TITLE"),
            background=self._environ.get("BRANDING_BACKGROUND"),
            branding_dir=Path(branding_dir),
        )
