import pytest
from apolo_sdk import Client, Cluster, AppsConfig
from yarl import URL

# Register pytest plugins for fixtures
pytest_plugins = [
    "apolo_app_types_fixtures.apolo_clients",
    "apolo_app_types_fixtures.constants",
]


@pytest.fixture
def apolo_cluster_config():
    return Cluster(
        name="cluster",
        orgs=[],
        registry_url=URL(""),
        storage_url=URL(""),
        users_url=URL(""),
        monitoring_url=URL(""),
        secrets_url=URL(""),
        disks_url=URL(""),
        buckets_url=URL(""),
        resource_pools={},
        presets={},
        apps=AppsConfig(),
    )


@pytest.fixture
def apolo_client(setup_clients: Client, apolo_cluster_config: Cluster):
    apolo_sdk_client = setup_clients

    async def _get_secret(key: str) -> bytes:
        return f"{key}-value".encode()

    apolo_sdk_client.config.clusters = {apolo_cluster_config.name: apolo_cluster_config}
    apolo_sdk_client.secrets.get = _get_secret
    return apolo_sdk_client
