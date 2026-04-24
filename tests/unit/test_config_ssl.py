import pytest

from launchpad.config import EnvironConfigFactory


@pytest.fixture
def minimal_env() -> dict[str, str]:
    """Provide minimal valid environment for config factory."""
    return {
        "KEYCLOAK_URL": "keycloak.example.local",
        "KEYCLOAK_REALM": "test-realm",
        "APOLO_PASSED_CONFIG": "e30=",  # base64 of '{}'
        "SELF_DOMAIN": "example.local",
        "WEB_DOMAIN": "app.example.local",
        "BASE_DOMAIN": "example.local",
        "AUTH_MIDDLEWARE_NAME": "auth",
        "DB_HOST": "db",
        "DB_USER": "user",
        "DB_PASSWORD": "pw",
        "DB_NAME": "db",
    }


@pytest.fixture
def factory(minimal_env: dict[str, str]) -> EnvironConfigFactory:
    """Default factory using minimal env."""
    return EnvironConfigFactory(environ=minimal_env.copy())


@pytest.mark.parametrize(
    "ssl_value, expected",
    [
        ("true", True),
        ("false", False),
    ],
)
def test_keycloak_ssl_verify_true_and_false(
    minimal_env: dict[str, str],
    ssl_value: str,
    expected: bool,
) -> None:
    env = minimal_env.copy()
    env["KEYCLOAK_SSL_VERIFY"] = ssl_value

    factory = EnvironConfigFactory(environ=env)
    cfg = factory.create_keycloak()

    assert cfg.ssl_verify is expected


def test_environ_factory_create_missing_vars_raises() -> None:
    factory = EnvironConfigFactory(environ={})

    with pytest.raises(KeyError):
        factory.create()
