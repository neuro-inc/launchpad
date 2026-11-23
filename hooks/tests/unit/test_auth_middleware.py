import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_auth_middleware_builds_forwarded_headers_from_the_request(
    tmp_path: Path,
) -> None:
    values = tmp_path / "values.yaml"
    values.write_text(
        yaml.safe_dump(
            {
                "apolo_app_id": "test-app",
                "LAUNCHPAD_ADMIN_PASSWORD": "test-admin",
                "dbPassword": "test-db",
                "authResponseHeaders": ["X-Auth-Request-Email"],
            }
        )
    )
    rendered = subprocess.check_output(
        ["helm", "template", "test", str(ROOT / "charts/launchpad"), "-f", str(values)],
        text=True,
    )
    (middleware,) = [
        item
        for item in yaml.safe_load_all(rendered)
        if item and item["kind"] == "Middleware"
    ]
    assert middleware["metadata"]["name"] == "launchpad-test-app-auth-middleware"
    assert middleware["spec"]["forwardAuth"] == {
        "address": "https://launchpad-test-app-api.apps.dev.apolo.us/auth/authorize",
        "trustForwardHeader": False,
        "authResponseHeaders": ["X-Auth-Request-Email"],
    }
