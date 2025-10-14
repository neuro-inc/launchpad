from fastapi.testclient import TestClient

from launchpad.config import Config


def test_ping_endpoint(app_client: TestClient) -> None:
    response = app_client.get("/ping")
    assert response.status_code == 200
    assert response.text == "Pong"


def test_config_endpoint(app_client: TestClient, config: Config) -> None:
    response = app_client.get("/config")
    assert response.status_code == 200
    assert response.json() == {
        "keycloak": {
            "url": str(config.keycloak.url),
            "realm": config.keycloak.realm,
        },
    }
