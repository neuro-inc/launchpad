"""Test the Release workflow's GitHub CLI steps without publishing anything."""

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parent.parent / "workflows/release.yml"


def shell_step(name: str) -> tuple[str, bool]:
    step = WORKFLOW.read_text().split(f"      - name: {name}\n", 1)[1]
    step = step.split("\n      - ", 1)[0]
    return textwrap.dedent(
        step.split("        run: |\n", 1)[1]
    ), "        shell: bash\n" in step


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.outputs = self.root / "outputs"
        self.requests = self.root / "requests"
        self.revision = "a" * 40
        self.run_metadata: dict[str, str] = {
            "conclusion": "success",
            "workflowName": "CI",
            "headBranch": "master",
            "headSha": self.revision,
            "event": "push",
        }

    def execute(
        self, name: str = "Select successful master CI", **environment: str
    ) -> subprocess.CompletedProcess[str]:
        self.outputs.unlink(missing_ok=True)
        self.requests.unlink(missing_ok=True)
        mock = """
            gh() {
              printf '%s\\n' "$*" >> "$REQUESTS"
              case "$1 $2" in
                'run list') printf '%s\\n' "$MOCK_RUN_ID" ;;
                'run view') printf '%s\\n' "$MOCK_RUN"; return "${MOCK_VIEW_FAILURE:-0}" ;;
                'api '*) printf '%s\\n' "$MOCK_ARTIFACT_IDS" ;;
                'release '*) return "${MOCK_RELEASE_FAILURE:-0}" ;;
                *) return 99 ;;
              esac
            }
        """
        script, explicit_bash = shell_step(name)
        return subprocess.run(
            [
                "bash",
                "-e",
                *(["-o", "pipefail"] if explicit_bash else []),
                "-c",
                textwrap.dedent(mock) + script,
            ],
            env={
                **os.environ,
                "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_OUTPUT": str(self.outputs),
                "RELEASE_REVISION": self.revision,
                "BUILD_RUN_ID": "42",
                "MOCK_RUN_ID": "42",
                "MOCK_RUN": json.dumps(self.run_metadata),
                "MOCK_ARTIFACT_IDS": "123",
                "RUNNER_TEMP": str(self.root),
                "RELEASE_TAG": "v1.2.3",
                "REQUESTS": str(self.requests),
                **environment,
            },
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

    def test_tag_push_selects_ci_for_the_exact_master_commit(self) -> None:
        result = self.execute(GITHUB_EVENT_NAME="push", BUILD_RUN_ID="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.outputs.read_text(), "run_id=42\nartifact_id=123\n")
        requests = self.requests.read_text().splitlines()
        self.assertIn("--workflow ci.yaml --branch master", requests[0])
        self.assertIn(f"--commit {self.revision} --status success", requests[0])
        self.assertIn("--paginate", requests[-1])
        self.assertIn(
            '.name == "launchpad-release" and .expired == false', requests[-1]
        )

    def test_manual_selection_does_not_select_another_run(self) -> None:
        self.run_metadata["event"] = "workflow_dispatch"
        result = self.execute(MOCK_RUN=json.dumps(self.run_metadata))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.requests.read_text().startswith("run view 42 "))

    def test_selection_rejects_unavailable_or_invalid_run_ids(self) -> None:
        for run_id in ("", "invalid", "0", "42\n43"):
            with self.subTest(run_id=run_id):
                result = self.execute(GITHUB_EVENT_NAME="push", MOCK_RUN_ID=run_id)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.outputs.exists())
        result = self.execute(BUILD_RUN_ID="invalid")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.requests.exists())

    def test_selection_requires_successful_master_ci_for_the_tagged_commit(
        self,
    ) -> None:
        for field, value in (
            ("conclusion", "failure"),
            ("workflowName", "Release"),
            ("headBranch", "feature"),
            ("headSha", "b" * 40),
            ("event", "pull_request"),
        ):
            with self.subTest(field=field):
                result = self.execute(
                    MOCK_RUN=json.dumps({**self.run_metadata, field: value})
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.outputs.exists())
                self.assertEqual(len(self.requests.read_text().splitlines()), 1)

    def test_selection_requires_one_unexpired_artifact(self) -> None:
        for identifiers in ("", "123\n456", "0", "invalid", "123\ninvalid"):
            with self.subTest(identifiers=identifiers):
                result = self.execute(MOCK_ARTIFACT_IDS=identifiers)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.outputs.exists())

    def test_failed_run_inspection_stops_after_partial_output(self) -> None:
        result = self.execute(MOCK_VIEW_FAILURE="7")
        self.assertEqual(result.returncode, 7)
        self.assertFalse(self.outputs.exists())
        self.assertEqual(len(self.requests.read_text().splitlines()), 1)

    def test_release_uploads_only_staged_files_without_clobbering(self) -> None:
        upload = self.root / "launchpad-release/upload"
        upload.mkdir(parents=True)
        (upload / "release.json").write_text("manifest")
        for create in ("true", "false"):
            with self.subTest(create=create):
                result = self.execute(
                    "Save the original release assets", CREATE_RELEASE=create
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                requests = self.requests.read_text().splitlines()
                self.assertEqual(len(requests), 1)
                self.assertIn(str(upload / "release.json"), requests[0])
                self.assertNotIn("--clobber", requests[0])
                self.assertNotIn("release edit", requests[0])
                if create == "true":
                    self.assertTrue(requests[0].startswith("release create v1.2.3 "))
                    self.assertIn("--verify-tag --draft", requests[0])
                else:
                    self.assertTrue(requests[0].startswith("release upload v1.2.3 "))

    def test_release_storage_errors_fail_the_step(self) -> None:
        result = self.execute(
            "Save the original release assets",
            CREATE_RELEASE="true",
            MOCK_RELEASE_FAILURE="1",
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
