from pathlib import Path

from .chart_helpers import render_chart


def test_auth_middleware_builds_forwarded_headers_from_the_request(
    tmp_path: Path,
) -> None:
    (middleware,) = [
        item for item in render_chart(tmp_path, {}) if item["kind"] == "Middleware"
    ]
    assert middleware["metadata"]["name"] == "launchpad-test-app-auth-middleware"
    assert middleware["spec"]["forwardAuth"] == {
        "address": "https://launchpad-test-app-api.apps.dev.apolo.us/auth/authorize",
        "trustForwardHeader": False,
        "authResponseHeaders": ["X-Auth-Request-Email"],
    }
