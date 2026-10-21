import os
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from yarl import URL

from launchpad.app_factory import create_app
from launchpad.auth.api import _validate_origin
from launchpad.config import Config
from launchpad.errors import Forbidden
from scripts.local_development.__main__ import create_config, main
from scripts.local_development.setup import setup_frontend


async def test_local_profile_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APOLO_CONFIG", raising=False)
    with patch("scripts.local_development.__main__.Factory") as factory:
        with pytest.raises(SystemExit, match="APOLO_CONFIG"):
            await create_config()
        factory.assert_not_called()


@pytest.mark.parametrize("variable", ["APOLO_PASSED_CONFIG", "NEURO_PASSED_CONFIG"])
async def test_passed_config_is_rejected(variable: str) -> None:
    with patch.dict(os.environ, {"APOLO_CONFIG": "/tmp/profile", variable: "test"}):
        with pytest.raises(SystemExit, match="Unset passed configurations"):
            await create_config()


@pytest.fixture
def platform_factory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[MagicMock]:
    monkeypatch.setenv("APOLO_CONFIG", str(tmp_path))
    (tmp_path / "db").touch()
    monkeypatch.delenv("APOLO_PASSED_CONFIG", raising=False)
    monkeypatch.delenv("NEURO_PASSED_CONFIG", raising=False)
    client = AsyncMock()
    client.config.username = "developer"
    client.config.cluster_name = "test-cluster"
    client.config.org_name = "test-org"
    client.config.project_name_or_raise = "test-project"
    client.config.api_url = URL("https://api.example.test:8443/api/v1")
    client.config.token.return_value = "test-platform-token"
    client.__aenter__.return_value = client
    with patch("scripts.local_development.__main__.Factory") as factory:
        factory.return_value.get = AsyncMock(return_value=client)
        yield factory


@pytest.fixture
async def local_config(platform_factory: MagicMock) -> Config:
    return await create_config()


async def test_local_profile_is_explicit(
    platform_factory: MagicMock, tmp_path: Path
) -> None:
    await create_config()
    platform_factory.assert_called_once_with(path=tmp_path)


def test_local_configuration(local_config: Config) -> None:
    config = local_config
    assert config.apolo.cluster == "test-cluster"
    assert config.apolo.org_name == "test-org"
    assert config.apolo.project_name == "test-project"
    assert config.apolo.apps_api_url == "https://api.example.test:8443/apis/apps"
    assert config.apolo.token == "test-platform-token"
    assert config.apps is None
    assert config.auth_bypass_path_prefixes is None
    assert config.server.host == "127.0.0.1"
    assert config.keycloak.url == URL("http://localhost:18081")


async def test_profile_output_excludes_credentials(
    platform_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    await create_config()
    output = capsys.readouterr().out
    assert "developer" in output
    assert "test-project" in output
    assert "test-platform-token" not in output


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("http://dev.localhost:13000", True),
        ("http://untrusted.example.test:13000", False),
    ],
)
def test_local_callback_origin(
    local_config: Config, origin: str, allowed: bool
) -> None:
    request = Request(
        {
            "type": "http",
            "app": SimpleNamespace(config=local_config),
            "headers": [(b"origin", origin.encode())],
        }
    )
    if allowed:
        _validate_origin(request)
    else:
        with pytest.raises(Forbidden):
            _validate_origin(request)


async def test_missing_profile_does_not_fall_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile = tmp_path / "missing"
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "db").touch()
    monkeypatch.setenv("APOLO_CONFIG", str(profile))
    monkeypatch.setenv("NEUROMATION_CONFIG", str(legacy))
    monkeypatch.delenv("APOLO_PASSED_CONFIG", raising=False)
    monkeypatch.delenv("NEURO_PASSED_CONFIG", raising=False)
    with patch("scripts.local_development.__main__.Factory") as factory:
        with pytest.raises(SystemExit, match="Authenticate the selected"):
            await create_config()
        factory.assert_not_called()


@pytest.fixture
def local_client(local_config: Config) -> Iterator[TestClient]:
    with (
        patch(
            "scripts.local_development.__main__.create_config",
            new=AsyncMock(return_value=local_config),
        ),
        patch("scripts.local_development.__main__.uvicorn.run") as run,
        patch("launchpad.app_factory.sync_db"),
    ):
        main()
    client = TestClient(run.call_args.args[0])
    try:
        yield client
    finally:
        client.close()


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("http://dev.localhost:13000", True),
        ("https://dev.localhost", False),
        ("http://untrusted.example.test:13000", False),
    ],
)
def test_local_cors_policy(
    local_client: TestClient, origin: str, allowed: bool
) -> None:
    response = local_client.options(
        "/ping",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == (200 if allowed else 400)
    assert response.headers.get("access-control-allow-origin") == (
        origin if allowed else None
    )
    response = local_client.get("/ping", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == (
        origin if allowed else None
    )


@pytest.mark.parametrize("cors_origins", [None, []])
def test_factory_default_and_empty_cors(
    local_config: Config, cors_origins: list[str] | None
) -> None:
    with patch("launchpad.app_factory.sync_db"):
        app = create_app(local_config, cors_origins=cors_origins)
    client = TestClient(app)
    try:
        response = client.options(
            "/ping",
            headers={
                "Origin": "https://dev.localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
    finally:
        client.close()
    assert response.status_code == (200 if cors_origins is None else 400)
    assert response.headers.get("access-control-allow-origin") == (
        "https://dev.localhost" if cors_origins is None else None
    )


def test_setup_creates_private_environment(tmp_path: Path) -> None:
    path = tmp_path / ".env.local"
    assert setup_frontend(path)
    assert path.stat().st_mode & 0o777 == 0o600
    values = dict(line.split("=", 1) for line in path.read_text().splitlines())
    assert values["NEXT_PUBLIC_ENVIRONMENT"] == "local"
    assert values["NEXT_PUBLIC_SITE_URL"] == "http://dev.localhost:8080"
    assert values["NEXTAUTH_URL"] == "http://dev.localhost:13000"
    assert len(bytes.fromhex(values["NEXTAUTH_SECRET"])) == 32
    original = path.read_bytes()
    assert not setup_frontend(path)
    assert path.read_bytes() == original


def test_setup_preserves_existing_settings(tmp_path: Path) -> None:
    path = tmp_path / ".env.local"
    original = b"NEXTAUTH_SECRET=existing-secret\nCUSTOM_SETTING=preserve\n"
    path.write_bytes(original)
    path.chmod(0o640)
    assert not setup_frontend(path)
    assert path.read_bytes() == original
    assert path.stat().st_mode & 0o777 == 0o640
