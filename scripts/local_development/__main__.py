"""Run the backend with local PostgreSQL and Keycloak."""

import asyncio
import os
from pathlib import Path

import uvicorn
from apolo_sdk import Factory
from yarl import URL

from launchpad.app_factory import create_app
from launchpad.config import (
    ApoloConfig,
    BrandingConfig,
    Config,
    KeycloakConfig,
    PostgresConfig,
    ServerConfig,
)


async def create_config() -> Config:
    if not os.environ.get("APOLO_CONFIG"):
        raise SystemExit(
            "Set APOLO_CONFIG to a dedicated development profile directory."
        )
    if os.environ.get("APOLO_PASSED_CONFIG") or os.environ.get("NEURO_PASSED_CONFIG"):
        raise SystemExit("Unset passed configurations before using the local launcher.")

    profile = Path(os.environ["APOLO_CONFIG"]).expanduser()
    if not (profile / "db").is_file():
        raise SystemExit(
            "Authenticate the selected APOLO_CONFIG profile before startup."
        )

    async with await Factory(path=profile).get() as client:
        platform = client.config
        print(
            f"Apolo user={platform.username} cluster={platform.cluster_name} "
            f"organization={platform.org_name} project={platform.project_name_or_raise}"
        )
        return Config(
            postgres=PostgresConfig(
                dsn="postgresql+asyncpg://launchpad:local-development@127.0.0.1:15432/launchpad"
            ),
            keycloak=KeycloakConfig(
                url=URL("http://localhost:18081"), realm="launchpad"
            ),
            apolo=ApoloConfig(
                cluster=platform.cluster_name,
                org_name=platform.org_name,
                project_name=platform.project_name_or_raise,
                apps_api_url=str(platform.api_url.origin() / "apis/apps"),
                token=await platform.token(),
                self_domain="dev-api.localhost",
                web_app_domain="dev.localhost",
                base_domain="localhost",
                auth_middleware_name="local-development",
            ),
            branding=BrandingConfig(),
            apps=None,
            server=ServerConfig(host="127.0.0.1", port=8080),
            cors_origins=["http://dev.localhost:13000"],
        )


def main() -> None:
    config = asyncio.run(create_config())
    app = create_app(config)
    uvicorn.run(app, host=config.server.host, port=config.server.port)


if __name__ == "__main__":
    main()
