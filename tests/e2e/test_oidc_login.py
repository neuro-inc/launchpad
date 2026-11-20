"""Exercise Launchpad's real OIDC login against the pinned Keycloak image."""

import asyncio
import json
import logging
import os
import secrets
import signal
import socket
import ssl
import subprocess
from contextlib import suppress
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import urljoin, urlsplit

import pytest
import uvicorn
import yaml
from httpx2 import AsyncClient, RequestError
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.postgres import PostgresContainer
from yarl import URL

from launchpad.app_factory import create_app
from launchpad.config import (
    ApoloConfig,
    BrandingConfig,
    Config,
    KeycloakConfig,
    PostgresConfig,
)


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
LOCAL_STACK = ROOT / "scripts/local_development"


class LoginForm(HTMLParser):
    action: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form" and attributes.get("id") == "kc-form-login":
            self.action = attributes.get("action")


async def wait_for_http(client: AsyncClient, url: str) -> None:
    async with asyncio.timeout(90):
        while True:
            try:
                if (await client.get(url, timeout=2)).status_code == 200:
                    return
            except RequestError:
                pass
            await asyncio.sleep(0.25)


async def check_login(client: AsyncClient, frontend: str, api: str, kc: str) -> None:
    callback = f"{frontend}/api/auth/callback/keycloak"
    protected_url = f"{api}/api/v1/apps"
    assert (await client.get(protected_url)).status_code == 401
    anonymous = await client.get(f"{frontend}/apps")
    assert anonymous.is_redirect
    assert urlsplit(anonymous.headers["location"]).path == "/auth"

    csrf = await client.get(f"{frontend}/api/auth/csrf")
    assert csrf.status_code == 200
    sign_in = await client.post(
        f"{frontend}/api/auth/signin/keycloak",
        data={
            "csrfToken": csrf.json()["csrfToken"],
            "callbackUrl": f"{frontend}/apps",
            "json": "true",
        },
    )
    assert sign_in.status_code == 200
    auth_url = sign_in.json()["url"]
    assert auth_url.startswith(f"{kc}/realms/launchpad/protocol/openid-connect/auth?")
    login = await client.get(auth_url)
    assert login.status_code == 200
    form = LoginForm()
    form.feed(login.text)
    assert form.action
    action = urljoin(auth_url, form.action)
    assert action.startswith(f"{kc}/realms/launchpad/login-actions/")
    login = await client.post(
        action, data={"username": "developer", "password": "local-development"}
    )
    assert login.is_redirect
    redirect = login.headers["location"]
    assert redirect.partition("?")[0] == callback
    signed_in = await client.get(redirect)
    assert signed_in.is_redirect
    assert signed_in.headers["location"] == f"{frontend}/apps"

    session = await client.get(f"{frontend}/api/auth/session")
    assert session.status_code == 200
    session_data = session.json()
    assert session_data["user"]["email"] == "developer@example.test"
    assert "admin" in session_data["client_roles"]
    assert (await client.get(f"{frontend}/apps")).status_code == 200
    authorized = await client.get(
        protected_url,
        headers={"Authorization": f"Bearer {session_data['accessToken']}"},
    )
    assert authorized.status_code == 200
    assert authorized.json()["items"] == []


async def test_keycloak_login_through_launchpad(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="httpx2")
    next_bin = FRONTEND / "node_modules/.bin/next"
    assert next_bin.is_file(), "Install frontend dependencies with npm ci first."
    with socket.socket() as reserved_port:
        reserved_port.bind(("127.0.0.1", 0))
        frontend_port = reserved_port.getsockname()[1]
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    realm = (
        (LOCAL_STACK / "realm.json")
        .read_text()
        .replace("http://dev.localhost:13000", frontend_url)
    )
    realm_file = tmp_path / "launchpad-realm.json"
    realm_file.write_text(realm)
    services = yaml.safe_load((LOCAL_STACK / "compose.yaml").read_text())["services"]
    certificate = tmp_path / "keycloak.crt"
    key = tmp_path / "keycloak.key"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-subj",
            "/CN=127.0.0.1",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
            "-days",
            "1",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        check=True,
        capture_output=True,
    )
    # The container's non-root user reads this file through a read-only bind mount.
    key.chmod(0o644)
    tls = ssl.create_default_context(cafile=str(certificate))

    # Next derives this API hostname in local mode. Resolve it only in the test process.
    resolver = tmp_path / "loopback.cjs"
    resolver.write_text(
        "const dns = require('node:dns');\n"
        "const lookup = dns.lookup;\n"
        "dns.lookup = (host, ...args) => "
        "lookup(host === 'dev-api.localhost' ? '127.0.0.1' : host, ...args);\n"
    )
    with (
        PostgresContainer(services["postgres"]["image"], driver="asyncpg") as postgres,
        DockerContainer(services["keycloak"]["image"])
        .with_exposed_ports(8443)
        .with_env("KC_HTTPS_CERTIFICATE_FILE", "/run/keycloak.crt")
        .with_env("KC_HTTPS_CERTIFICATE_KEY_FILE", "/run/keycloak.key")
        .with_volume_mapping(certificate, "/run/keycloak.crt")
        .with_volume_mapping(key, "/run/keycloak.key")
        .with_volume_mapping(
            realm_file, "/opt/keycloak/data/import/launchpad-realm.json"
        )
        .with_command("start-dev --import-realm")
        .waiting_for(
            LogMessageWaitStrategy("Listening on:").with_startup_timeout(180)
        ) as keycloak,
        socket.socket() as api_listener,
        patch("launchpad.lifespan.ApoloClientFactory") as apolo_factory,
        (tmp_path / "frontend.log").open("w+") as frontend_log,
    ):
        api_listener.bind(("127.0.0.1", 0))
        api_port = api_listener.getsockname()[1]
        api_url = f"http://127.0.0.1:{api_port}"
        keycloak_url = f"https://127.0.0.1:{keycloak.get_exposed_port(8443)}"
        apolo_factory.return_value.get = AsyncMock(return_value=AsyncMock())
        config = Config(
            postgres=PostgresConfig(dsn=postgres.get_connection_url()),
            keycloak=KeycloakConfig(url=URL(keycloak_url), realm="launchpad"),
            apolo=ApoloConfig(
                cluster="local",
                org_name="local",
                project_name="local",
                apps_api_url="http://127.0.0.1:9",
                token="local",
                self_domain="dev-api.localhost",
                web_app_domain="127.0.0.1",
                base_domain="localhost",
                auth_middleware_name="test",
            ),
            branding=BrandingConfig(branding_dir=tmp_path / "branding"),
            apps=None,
            cors_origins=[frontend_url],
        )
        app = await asyncio.to_thread(create_app, config)
        api = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        api_task = asyncio.create_task(api.serve(sockets=[api_listener]))
        try:
            frontend = await asyncio.create_subprocess_exec(
                "node",
                str(next_bin),
                "dev",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(frontend_port),
                cwd=FRONTEND,
                env={
                    **os.environ,
                    "KEYCLOAK_CLIENT_SECRET": "",
                    "NEXTAUTH_SECRET": secrets.token_hex(32),
                    "NEXTAUTH_URL": frontend_url,
                    "NEXTAUTH_URL_INTERNAL": frontend_url,
                    "NEXT_PUBLIC_ENVIRONMENT": "local",
                    "NEXT_PUBLIC_SITE_URL": f"http://dev.localhost:{api_port}",
                    "NEXT_TELEMETRY_DISABLED": "1",
                    "NODE_EXTRA_CA_CERTS": str(certificate),
                    "NODE_OPTIONS": f"--require={json.dumps(str(resolver))}",
                },
                stdout=frontend_log,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                async with AsyncClient(
                    timeout=60, trust_env=False, verify=tls
                ) as client:
                    await wait_for_http(client, f"{api_url}/ping")
                    try:
                        await wait_for_http(client, f"{frontend_url}/api/health")
                    except TimeoutError as error:
                        frontend_log.seek(0)
                        raise AssertionError(frontend_log.read()[-2000:]) from error
                    await check_login(client, frontend_url, api_url, keycloak_url)
            finally:
                with suppress(ProcessLookupError):
                    os.killpg(frontend.pid, signal.SIGTERM)
                try:
                    await asyncio.wait_for(frontend.wait(), 10)
                except TimeoutError:
                    with suppress(ProcessLookupError):
                        os.killpg(frontend.pid, signal.SIGKILL)
                    await frontend.wait()
        finally:
            api.should_exit = True
            await asyncio.wait_for(api_task, 15)
