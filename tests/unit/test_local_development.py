import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request
from yarl import URL

from launchpad.auth.api import _validate_origin
from launchpad.errors import Forbidden
from scripts.local_development.__main__ import create_config


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


async def test_local_config_uses_selected_profile(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
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
        config = await create_config()
        factory.assert_called_once_with(path=tmp_path)
    assert config.apolo.cluster == "test-cluster"
    assert config.apolo.org_name == "test-org"
    assert config.apolo.project_name == "test-project"
    assert config.apolo.apps_api_url == "https://api.example.test:8443/apis/apps"
    assert config.apolo.token == "test-platform-token"
    assert config.apps is None
    assert config.auth_bypass_path_prefixes is None
    assert config.server.host == "127.0.0.1"
    assert config.keycloak.url == URL("http://localhost:18081")
    output = capsys.readouterr().out
    assert "developer" in output
    assert "test-project" in output
    assert "test-platform-token" not in output

    request = Request(
        {
            "type": "http",
            "app": SimpleNamespace(config=config),
            "headers": [(b"origin", b"http://dev.localhost:13000")],
        }
    )
    _validate_origin(request)
    request = Request(
        {
            "type": "http",
            "app": SimpleNamespace(config=config),
            "headers": [(b"origin", b"http://untrusted.example.test:13000")],
        }
    )
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
