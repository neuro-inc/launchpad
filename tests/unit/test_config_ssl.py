from launchpad.config import EnvironConfigFactory


def make_minimal_env() -> dict[str, str]:
    # minimal env required to construct keycloak config
    return {
        "KEYCLOAK_URL": "keycloak.example.local",
        "KEYCLOAK_REALM": "test-realm",
        # APOLO_PASSED_CONFIG minimal required for create()
        "APOLO_PASSED_CONFIG": "e30=",  # base64 of '{}'
        "SELF_DOMAIN": "example.local",
        "WEB_DOMAIN": "app.example.local",
        "BASE_DOMAIN": "example.local",
        "AUTH_MIDDLEWARE_NAME": "auth",
        # DB vars required by create_postgres
        "DB_HOST": "db",
        "DB_USER": "user",
        "DB_PASSWORD": "pw",
        "DB_NAME": "db",
    }


def test_keycloak_ssl_verify_true_and_false() -> None:
    env = make_minimal_env()
    env["KEYCLOAK_SSL_VERIFY"] = "true"
    factory = EnvironConfigFactory(environ=env)
    cfg = factory.create_keycloak()
    assert cfg.ssl_verify is True

    env["KEYCLOAK_SSL_VERIFY"] = "false"
    factory = EnvironConfigFactory(environ=env)
    cfg = factory.create_keycloak()
    assert cfg.ssl_verify is False


def test_environ_factory_create_missing_vars_raises() -> None:
    # missing required keys (KEYCLOAK_URL/REALM) should raise KeyError
    factory = EnvironConfigFactory(environ={})
    try:
        factory.create()
        raised = False
    except KeyError:
        raised = True
    assert raised
