import subprocess
from pathlib import Path
from typing import Any

import yaml


CHART = Path(__file__).resolve().parents[3] / "charts/launchpad"


def render_chart(tmp_path: Path, overrides: dict[str, object]) -> list[dict[str, Any]]:
    values = tmp_path / "values.yaml"
    values.write_text(
        yaml.safe_dump(
            {
                "apolo_app_id": "test-app",
                "LAUNCHPAD_ADMIN_PASSWORD": "test-admin",
                "keycloak": {"auth": {"adminPassword": "test-keycloak-admin"}},
                "dbPassword": "test-db",
                "postgresql": {"enabled": True},
                "authResponseHeaders": ["X-Auth-Request-Email"],
                **overrides,
            }
        )
    )
    rendered = subprocess.check_output(
        ["helm", "template", "test", str(CHART), "-f", str(values)],
        text=True,
        stderr=subprocess.PIPE,
    )
    return [item for item in yaml.safe_load_all(rendered) if item]
