import json
import re
import subprocess
from pathlib import Path

import pytest
from apolo_app_types.protocols.common import Preset
from apolo_apps_launchpad.inputs_processor import LaunchpadInputsProcessor
from apolo_apps_launchpad.types import (
    AppsConfig,
    LaunchpadAppInputs,
    LaunchpadWebAppConfig,
    NoQuickStartConfig,
)
from apolo_sdk import Client


CHART = Path(__file__).resolve().parents[4] / "charts/launchpad"
GOLDEN = Path(__file__).with_name("goldens") / "install.yaml"


async def test_launchpad_chart_render_matches_golden(
    apolo_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("APOLO_APP_GIT_REPO", raising=False)
    monkeypatch.delenv("APOLO_APP_GIT_REVISION", raising=False)
    monkeypatch.setenv("APP_IMAGE_TAG", "0.0.0")
    monkeypatch.setenv("APP_IMAGE_DIGEST", "sha256:" + "a" * 64)
    monkeypatch.setenv("FRONTEND_IMAGE_DIGEST", "sha256:" + "b" * 64)
    release = "launchpad-golden"
    namespace = "platform--test-org--test-project"
    values = await LaunchpadInputsProcessor(apolo_client).gen_extra_values(
        input_=LaunchpadAppInputs(
            launchpad_web_app_config=LaunchpadWebAppConfig(
                preset=Preset(name="cpu-small")
            ),
            apps_config=AppsConfig(
                quick_start_config=NoQuickStartConfig(no_quickstart=True)
            ),
        ),
        app_name=release,
        namespace=namespace,
        app_secrets_name="golden-app-secrets",
        app_id="golden-app",
    )
    values_path = tmp_path / "values.json"
    values_path.write_text(json.dumps(values))
    rendered = subprocess.check_output(
        [
            "helm",
            "template",
            release,
            str(CHART),
            "--namespace",
            namespace,
            "--kube-version",
            "1.31.0",
            "--values",
            str(values_path),
        ],
        text=True,
    )
    rendered = re.sub(r"[ \t]+$", "", rendered, flags=re.MULTILINE)
    rendered = re.sub(r"\n\n+(---\n|\Z)", r"\n\1", rendered)

    if request.config.getoption("--update-goldens"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(rendered)
    assert GOLDEN.exists(), f"{GOLDEN} is missing, run make update-goldens"
    assert rendered == GOLDEN.read_text(), "Chart changed. Run make update-goldens."
