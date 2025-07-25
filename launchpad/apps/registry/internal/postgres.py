from launchpad.apps.registry.model import App


APP_NAME_POSTGRES = "postgres"


def gen_postgres_definition(preset: str) -> App:
    return App(
        template_name="postgres",
        template_version="v25.5.0",
        name=APP_NAME_POSTGRES,
        is_internal=True,
        is_shared=True,
        input={
            "postgres_config": {
                "postgres_version": "16",
                "instance_replicas": 1,
                "instance_size": 1,
                "db_users": [{"name": "user", "db_names": ["openwebui"]}],
            },
            "pg_bouncer": {"replicas": 1, "preset": {"name": preset}},
            "backup": {"enable": False},
            "displayName": APP_NAME_POSTGRES,
            "preset": {"name": preset},
        },
    )
