from typing import Any

from launchpad.apps.registry.base import App
from launchpad.apps.registry.internal.context import InternalAppContext

APP_NAME_POSTGRES = "postgres"


class PostgresApp(App[InternalAppContext]):
    name = APP_NAME_POSTGRES
    template_name = "postgres"
    template_version = "v25.5.0"
    is_internal = True
    is_shared = True
    verbose_name = "PostgreSQL"
    description_short = "PostgreSQL"
    description_long = "PostgreSQL"
    logo = ""
    documentation_urls = []
    external_urls = []
    tags = []

    async def _generate_inputs(self) -> dict[str, Any]:
        return self._context.merge_with_inputs(
            inputs={
                "postgres_config": {
                    "postgres_version": "16",
                    "instance_replicas": 1,
                    "instance_size": 1,
                    "db_users": [{"name": "user", "db_names": ["openwebui"]}],
                },
                "pg_bouncer": {"replicas": 1},
                "backup": {"enable": False},
                "displayName": APP_NAME_POSTGRES,
            }
        )
