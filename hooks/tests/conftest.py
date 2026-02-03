import pytest

# Register pytest plugins for fixtures
pytest_plugins = [
    "apolo_app_types_fixtures.apolo_clients",
    "apolo_app_types_fixtures.constants",
]


@pytest.fixture
def apolo_client(setup_clients):
    apolo_sdk_client = setup_clients

    async def _get_secret(key: str) -> bytes:
        return f"{key}-value".encode()

    apolo_sdk_client.secrets.get = _get_secret
    return apolo_sdk_client
