import json
import os
from base64 import b64encode
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from yarl import URL

from launchpad.config import (
    Config,
    ServerConfig,
    KeycloakConfig,
    ApoloConfig,
    AppsConfig,
    EnvironConfigFactory,
)


@pytest.fixture
def mock_environ() -> Iterator[None]:
    with patch.dict(
        os.environ,
        {
            "HOST": "127.0.0.1",
            "PORT": "8000",
            "DB_HOST": "localhost",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpassword",
            "DB_NAME": "testdb",
            "DB_PORT": "5432",
            "KEYCLOAK_URL": "keycloak.example.com",
            "KEYCLOAK_REALM": "testrealm",
            "APOLO_PASSED_CONFIG": b64encode(
                json.dumps(
                    {
                        "url": "https://apolo.example.com",
                        "cluster": "test-cluster",
                        "org_name": "test-org",
                        "project_name": "test-project",
                        "token": "test-token",
                    }
                ).encode()
            ).decode(),
            "SELF_DOMAIN": "https://self.example.com",
            "BASE_DOMAIN": "https://base.example.com",
            "AUTH_MIDDLEWARE_NAME": "test-middleware",
            "LAUNCHPAD_INITIAL_CONFIG": json.dumps(
                {
                    "vllm": {"setting": "vllm_value"},
                    "postgres": {"setting": "postgres_value"},
                    "text-embeddings": {"setting": "embeddings_value"},
                }
            ),
        },
        clear=True,
    ):
        yield


def test_environ_config_factory_create_server(mock_environ: None) -> None:
    factory = EnvironConfigFactory()
    config = factory.create_server()
    assert config == ServerConfig(host="127.0.0.1", port=8000)


def test_environ_config_factory_create_postgres(mock_environ: None) -> None:
    factory = EnvironConfigFactory()
    config = factory.create_postgres()
    assert (
        config.dsn == "postgresql+asyncpg://testuser:testpassword@localhost:5432/testdb"
    )


def test_environ_config_factory_create_keycloak(mock_environ: None) -> None:
    factory = EnvironConfigFactory()
    config = factory.create_keycloak()
    assert config == KeycloakConfig(
        url=URL("https://keycloak.example.com"), realm="testrealm"
    )


def test_environ_config_factory_create_apolo(mock_environ: None) -> None:
    factory = EnvironConfigFactory()
    config = factory.create_apolo()
    assert config == ApoloConfig(
        cluster="test-cluster",
        org_name="test-org",
        project_name="test-project",
        apps_api_url="https://apolo.example.com/apis/apps",
        token="test-token",
        self_domain="https://self.example.com",
        base_domain="https://base.example.com",
        auth_middleware_name="test-middleware",
    )


def test_environ_config_factory_create_apps(mock_environ: None) -> None:
    factory = EnvironConfigFactory()
    config = factory.create_apps()
    assert config == AppsConfig(
        vllm={"setting": "vllm_value"},
        postgres={"setting": "postgres_value"},
        embeddings={"setting": "embeddings_value"},
    )


def test_environ_config_factory_create_full_config(mock_environ: None) -> None:
    factory = EnvironConfigFactory()
    config = factory.create()
    assert isinstance(config, Config)
    assert config.server.host == "127.0.0.1"
    assert (
        config.postgres.dsn
        == "postgresql+asyncpg://testuser:testpassword@localhost:5432/testdb"
    )
    assert config.keycloak.realm == "testrealm"
    assert config.apolo.cluster == "test-cluster"
    assert config.apps is not None
    assert config.apps.vllm == {"setting": "vllm_value"}


def test_environ_config_factory_create_apps_empty_config() -> None:
    """Test that empty LAUNCHPAD_INITIAL_CONFIG returns None for apps"""
    # Use EnvironConfigFactory with explicit environ dict to bypass .env loading
    environ = {
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "DB_HOST": "localhost",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpassword",
        "DB_NAME": "testdb",
        "KEYCLOAK_URL": "keycloak.example.com",
        "KEYCLOAK_REALM": "testrealm",
        "APOLO_PASSED_CONFIG": b64encode(
            json.dumps(
                {
                    "url": "https://apolo.example.com",
                    "cluster": "test-cluster",
                    "org_name": "test-org",
                    "project_name": "test-project",
                    "token": "test-token",
                }
            ).encode()
        ).decode(),
        "SELF_DOMAIN": "https://self.example.com",
        "BASE_DOMAIN": "https://base.example.com",
        "AUTH_MIDDLEWARE_NAME": "test-middleware",
        "LAUNCHPAD_INITIAL_CONFIG": "{}",  # Empty config
    }
    factory = EnvironConfigFactory(environ=environ)
    config = factory.create_apps()
    assert config is None


def test_environ_config_factory_create_apps_missing_config() -> None:
    """Test that missing LAUNCHPAD_INITIAL_CONFIG returns None for apps"""
    # Use EnvironConfigFactory with explicit environ dict to bypass .env loading
    environ = {
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "DB_HOST": "localhost",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpassword",
        "DB_NAME": "testdb",
        "KEYCLOAK_URL": "keycloak.example.com",
        "KEYCLOAK_REALM": "testrealm",
        "APOLO_PASSED_CONFIG": b64encode(
            json.dumps(
                {
                    "url": "https://apolo.example.com",
                    "cluster": "test-cluster",
                    "org_name": "test-org",
                    "project_name": "test-project",
                    "token": "test-token",
                }
            ).encode()
        ).decode(),
        "SELF_DOMAIN": "https://self.example.com",
        "BASE_DOMAIN": "https://base.example.com",
        "AUTH_MIDDLEWARE_NAME": "test-middleware",
        # LAUNCHPAD_INITIAL_CONFIG not set
    }
    factory = EnvironConfigFactory(environ=environ)
    config = factory.create_apps()
    assert config is None


def test_environ_config_factory_create_apps_incomplete_config() -> None:
    """Test that incomplete LAUNCHPAD_INITIAL_CONFIG returns None for apps"""
    # Use EnvironConfigFactory with explicit environ dict to bypass .env loading
    environ = {
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "DB_HOST": "localhost",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpassword",
        "DB_NAME": "testdb",
        "KEYCLOAK_URL": "keycloak.example.com",
        "KEYCLOAK_REALM": "testrealm",
        "APOLO_PASSED_CONFIG": b64encode(
            json.dumps(
                {
                    "url": "https://apolo.example.com",
                    "cluster": "test-cluster",
                    "org_name": "test-org",
                    "project_name": "test-project",
                    "token": "test-token",
                }
            ).encode()
        ).decode(),
        "SELF_DOMAIN": "https://self.example.com",
        "BASE_DOMAIN": "https://base.example.com",
        "AUTH_MIDDLEWARE_NAME": "test-middleware",
        "LAUNCHPAD_INITIAL_CONFIG": json.dumps(
            {
                "vllm": {"setting": "vllm_value"},
                # Missing postgres and text-embeddings
            }
        ),
    }
    factory = EnvironConfigFactory(environ=environ)
    config = factory.create_apps()
    assert config is None


def test_environ_config_factory_create_apps_invalid_json() -> None:
    """Test that invalid JSON in LAUNCHPAD_INITIAL_CONFIG returns None for apps"""
    # Use EnvironConfigFactory with explicit environ dict to bypass .env loading
    environ = {
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "DB_HOST": "localhost",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpassword",
        "DB_NAME": "testdb",
        "KEYCLOAK_URL": "keycloak.example.com",
        "KEYCLOAK_REALM": "testrealm",
        "APOLO_PASSED_CONFIG": b64encode(
            json.dumps(
                {
                    "url": "https://apolo.example.com",
                    "cluster": "test-cluster",
                    "org_name": "test-org",
                    "project_name": "test-project",
                    "token": "test-token",
                }
            ).encode()
        ).decode(),
        "SELF_DOMAIN": "https://self.example.com",
        "BASE_DOMAIN": "https://base.example.com",
        "AUTH_MIDDLEWARE_NAME": "test-middleware",
        "LAUNCHPAD_INITIAL_CONFIG": "not valid json {{{",  # Invalid JSON
    }
    factory = EnvironConfigFactory(environ=environ)
    config = factory.create_apps()
    assert config is None


def test_environ_config_factory_create_apps_whitespace_only() -> None:
    """Test that whitespace-only LAUNCHPAD_INITIAL_CONFIG returns None for apps"""
    # Use EnvironConfigFactory with explicit environ dict to bypass .env loading
    environ = {
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "DB_HOST": "localhost",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpassword",
        "DB_NAME": "testdb",
        "KEYCLOAK_URL": "keycloak.example.com",
        "KEYCLOAK_REALM": "testrealm",
        "APOLO_PASSED_CONFIG": b64encode(
            json.dumps(
                {
                    "url": "https://apolo.example.com",
                    "cluster": "test-cluster",
                    "org_name": "test-org",
                    "project_name": "test-project",
                    "token": "test-token",
                }
            ).encode()
        ).decode(),
        "SELF_DOMAIN": "https://self.example.com",
        "BASE_DOMAIN": "https://base.example.com",
        "AUTH_MIDDLEWARE_NAME": "test-middleware",
        "LAUNCHPAD_INITIAL_CONFIG": "   \n  \t  ",  # Whitespace only
    }
    factory = EnvironConfigFactory(environ=environ)
    config = factory.create_apps()
    assert config is None
