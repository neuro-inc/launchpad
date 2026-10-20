"""Test complete App release assembly and publication without rebuilding."""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from release import (
    REPOSITORIES,
    Release,
    assemble,
    command,
    download_release,
    head,
    load_release,
    publish,
    publish_development,
    registry_digest,
    verify_release,
    write_json,
)


class ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(
            os.environ,
            {
                "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                "GITHUB_REF_TYPE": "branch",
                "GITHUB_REF_NAME": "master",
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_REF": "refs/heads/master",
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.previous)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Release tests")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("config", "commit.gpgsign", "false")
        for name in (
            "Dockerfile",
            "launchpad/app.py",
            "frontend/src/app.ts",
            "hooks/hooks.Dockerfile",
            ".apolo/types.py",
            "charts/launchpad/values.yaml",
            ".github/workflows/ci.yaml",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("initial\n")
        (self.root / "charts/launchpad/Chart.yaml").write_text(
            "apiVersion: v2\nname: launchpad\nversion: 1.0.0\n"
        )
        (self.root / "charts/launchpad/values.yaml").write_text("replicaCount: 1\n")
        self.commit()
        self.base = self.root / "release-base"
        self.base.mkdir()
        self.images = {
            name: repository + "@sha256:" + str(index + 1) * 64
            for index, (name, repository) in enumerate(REPOSITORIES.items())
        }
        archive = self.base / "launchpad-1.0.0.tgz"
        archive.write_bytes(b"chart archive")
        self.release: Release = {
            "schema_version": 2,
            "source_revision": head(),
            "images": self.images,
            "chart": {
                "filename": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            },
        }
        write_json(self.base / "release.json", self.release)

    def git(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.PIPE
        ).strip()

    def commit(self) -> None:
        self.git("add", ".")
        self.git("commit", "-qm", "test source")

    def change(self, path: str) -> None:
        (self.root / path).write_text("changed\n")
        self.commit()

    def test_chart_checksum_and_path_are_validated(self) -> None:
        (self.base / "launchpad-1.0.0.tgz").write_bytes(b"tampered archive")
        with self.assertRaisesRegex(ValueError, "checksum"):
            verify_release(self.base, self.release["source_revision"])
        release = copy.deepcopy(self.release)
        release["chart"]["filename"] = "../launchpad-1.0.0.tgz"
        write_json(self.base / "release.json", release)
        with self.assertRaises(ValueError):
            load_release(self.base)

    def mock_publication(self) -> None:
        self.git("-c", "tag.gpgsign=false", "tag", "v1.2.3")
        self.run_metadata: dict[str, object] = {
            "conclusion": "success",
            "workflowName": "CI",
            "headBranch": "master",
            "headSha": self.release["source_revision"],
            "event": "push",
        }
        self.registry = {
            image: image.split("@", 1)[1] for image in self.images.values()
        }
        self.registry_writes: list[tuple[str, ...]] = []

        def execute(*args: str) -> str:
            if args[0] != "docker":
                return command(*args)
            self.registry_writes.append(args)
            self.registry[args[-2]] = self.registry[args[-1]]
            return ""

        def download(directory: Path, run_id: str) -> None:
            self.assertEqual(run_id, "42")
            shutil.copytree(self.base, directory, dirs_exist_ok=True)

        for mock in (
            patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}),
            patch(
                "release.gh",
                side_effect=lambda *args: self.release["source_revision"]
                if args[0] == "api"
                else json.dumps(self.run_metadata),
            ),
            patch("release.download_release", side_effect=download),
            patch(
                "release.registry_digest",
                side_effect=lambda reference, allow_missing=False: self.registry.get(
                    reference
                ),
            ),
            patch("release.command", side_effect=execute),
        ):
            mock.start()
            self.addCleanup(mock.stop)

    def test_publication_preserves_the_tested_combination_without_building(
        self,
    ) -> None:
        self.mock_publication()
        output = self.root / "publication"
        publish(output, "42", "v1.2.3")
        for name in ("release.json", self.release["chart"]["filename"]):
            self.assertEqual(
                (output / name).read_bytes(), (self.base / name).read_bytes()
            )
        self.assertEqual(len(self.registry_writes), 3)
        for arguments in self.registry_writes:
            self.assertEqual(
                arguments[:6],
                (
                    "docker",
                    "buildx",
                    "imagetools",
                    "create",
                    "--prefer-index=false",
                    "--tag",
                ),
            )
        for component, image in self.images.items():
            self.assertEqual(
                self.registry[REPOSITORIES[component] + ":v1.2.3"],
                image.split("@", 1)[1],
            )

    def test_publication_retry_accepts_only_matching_existing_aliases(self) -> None:
        self.mock_publication()
        for component, image in self.images.items():
            self.registry[REPOSITORIES[component] + ":v1.2.3"] = image.split("@", 1)[1]
        publish(self.root / "publication", "42", "v1.2.3")
        self.assertEqual(self.registry_writes, [])

    def test_publication_retry_completes_matching_partial_publication(self) -> None:
        self.mock_publication()
        self.registry[REPOSITORIES["backend"] + ":v1.2.3"] = self.images[
            "backend"
        ].split("@", 1)[1]
        publish(self.root / "publication", "42", "v1.2.3")
        self.assertEqual(len(self.registry_writes), 2)
        for component, image in self.images.items():
            self.assertEqual(
                self.registry[REPOSITORIES[component] + ":v1.2.3"],
                image.split("@", 1)[1],
            )

    def test_publication_rejects_an_existing_conflict_before_any_write(self) -> None:
        self.mock_publication()
        self.registry[REPOSITORIES["hook"] + ":v1.2.3"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(ValueError, "already selects a different image"):
            publish(self.root / "publication", "42", "v1.2.3")
        self.assertEqual(self.registry_writes, [])

    def test_publication_rejects_a_missing_source_before_any_write(self) -> None:
        self.mock_publication()
        del self.registry[self.images["hook"]]
        with self.assertRaisesRegex(ValueError, "tested digest"):
            publish(self.root / "publication", "42", "v1.2.3")
        self.assertEqual(self.registry_writes, [])

    def test_publication_requires_a_successful_master_ci_source(self) -> None:
        self.mock_publication()
        for field, value in (
            ("conclusion", "failure"),
            ("headBranch", "feature"),
            ("event", "pull_request"),
            ("workflowName", "Release"),
            ("headSha", "f" * 40),
        ):
            with self.subTest(field=field):
                original = self.run_metadata[field]
                self.run_metadata[field] = value
                with self.assertRaises(ValueError):
                    publish(self.root / "publication", "42", "v1.2.3")
                self.run_metadata[field] = original
                self.assertEqual(self.registry_writes, [])

    def test_publication_rejects_changed_tag_inputs_before_any_write(self) -> None:
        self.mock_publication()
        self.change("frontend/src/app.ts")
        self.git("-c", "tag.gpgsign=false", "tag", "v1.2.4")
        with self.assertRaisesRegex(ValueError, "exact tagged commit"):
            publish(self.root / "publication", "42", "v1.2.4")
        self.assertEqual(self.registry_writes, [])

    def test_tag_push_selects_the_successful_ci_run_for_its_commit(self) -> None:
        self.mock_publication()
        with (
            patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/tags/v1.2.3"},
            ),
            patch(
                "release.gh",
                side_effect=[
                    "42",
                    json.dumps(self.run_metadata),
                ],
            ) as api,
        ):
            publish(self.root / "publication", "", "v1.2.3")
        arguments = api.call_args_list[0].args
        for option, value in (
            ("--commit", self.release["source_revision"]),
            ("--branch", "master"),
            ("--workflow", "ci.yaml"),
            ("--status", "success"),
        ):
            self.assertEqual(arguments[arguments.index(option) + 1], value)
        self.assertEqual(len(self.registry_writes), 3)

    def test_automatic_publication_requires_available_ci_for_the_exact_commit(
        self,
    ) -> None:
        self.mock_publication()
        with patch.dict(
            os.environ,
            {"GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/tags/v1.2.3"},
        ):
            with (
                patch("release.gh", return_value=""),
                self.assertRaisesRegex(ValueError, "successful master CI"),
            ):
                publish(self.root / "publication", "", "v1.2.3")
            self.run_metadata["headSha"] = "f" * 40
            with (
                patch(
                    "release.gh",
                    side_effect=[
                        "42",
                        json.dumps(self.run_metadata),
                    ],
                ),
                self.assertRaisesRegex(ValueError, "exact tagged commit"),
            ):
                publish(self.root / "publication", "", "v1.2.3")
        self.assertEqual(self.registry_writes, [])

    def test_tag_push_cannot_publish_a_different_tag(self) -> None:
        self.mock_publication()
        with (
            patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/tags/v1.2.4"},
            ),
            self.assertRaises(ValueError),
        ):
            publish(self.root / "publication", "42", "v1.2.3")
        self.assertEqual(self.registry_writes, [])

    def test_development_publication_updates_existing_aliases_without_building(
        self,
    ) -> None:
        self.mock_publication()
        for repository in REPOSITORIES.values():
            self.registry[repository + ":master"] = "sha256:" + "f" * 64
        publish_development(self.base)
        self.assertEqual(len(self.registry_writes), 3)
        for component, image in self.images.items():
            self.assertEqual(
                self.registry[REPOSITORIES[component] + ":master"],
                image.split("@", 1)[1],
            )
        publish_development(self.base)
        self.assertEqual(len(self.registry_writes), 3)

    def test_development_publication_rejects_other_refs_and_unverified_sources(
        self,
    ) -> None:
        self.mock_publication()
        for event, ref in (
            ("pull_request", "refs/heads/master"),
            ("push", "refs/heads/feature"),
            ("push", "refs/tags/v1.2.3"),
        ):
            with (
                patch.dict(os.environ, {"GITHUB_EVENT_NAME": event, "GITHUB_REF": ref}),
                self.assertRaises(ValueError),
            ):
                publish_development(self.base)
        del self.registry[self.images["hook"]]
        with self.assertRaisesRegex(ValueError, "tested digest"):
            publish_development(self.base)
        self.assertEqual(self.registry_writes, [])

    def test_development_publication_rejects_a_superseded_master_run(self) -> None:
        self.mock_publication()
        with (
            patch("release.gh", return_value="f" * 40),
            self.assertRaisesRegex(ValueError, "no longer matches master"),
        ):
            publish_development(self.base)
        self.assertEqual(self.registry_writes, [])

    def test_development_publication_requires_its_original_current_combination(
        self,
    ) -> None:
        self.mock_publication()
        (self.root / "notes.txt").write_text("documentation only\n")
        self.commit()
        with self.assertRaisesRegex(ValueError, "tested source commit"):
            publish_development(self.base)
        self.assertEqual(self.registry_writes, [])

    def test_publication_requires_an_authorized_event_and_valid_inputs(
        self,
    ) -> None:
        self.mock_publication()
        for event, ref, run_id, tag in (
            ("push", "refs/heads/master", "42", "v1.2.3"),
            ("workflow_dispatch", "refs/heads/feature", "42", "v1.2.3"),
            ("workflow_dispatch", "refs/tags/v1.2.3", "42", "v1.2.3"),
            ("workflow_dispatch", "refs/heads/master", "", "v1.2.3"),
            ("workflow_dispatch", "refs/heads/master", "invalid", "v1.2.3"),
            ("workflow_dispatch", "refs/heads/master", "42", "release"),
            ("workflow_dispatch", "refs/heads/master", "42", "v/unsafe"),
        ):
            with self.subTest(event=event, ref=ref, run_id=run_id, tag=tag):
                with (
                    patch.dict(
                        os.environ, {"GITHUB_EVENT_NAME": event, "GITHUB_REF": ref}
                    ),
                    self.assertRaises(ValueError),
                ):
                    publish(self.root / "publication", run_id, tag)
                self.assertEqual(self.registry_writes, [])

    def test_publication_rejects_an_unavailable_build_artifact(self) -> None:
        self.mock_publication()
        with (
            patch(
                "release.download_release",
                side_effect=ValueError(
                    "The selected App release artifact is unavailable."
                ),
            ),
            self.assertRaisesRegex(ValueError, "artifact is unavailable"),
        ):
            publish(self.root / "publication", "42", "v1.2.3")
        self.assertEqual(self.registry_writes, [])

    def test_publication_detects_an_alias_digest_change(self) -> None:
        self.mock_publication()

        def digest(reference: str, allow_missing: bool = False) -> str | None:
            if self.registry_writes and ":v1.2.3" in reference:
                return "sha256:" + "f" * 64
            return self.registry.get(reference)

        with (
            patch("release.registry_digest", side_effect=digest),
            self.assertRaisesRegex(ValueError, "alias changed the tested digest"),
        ):
            publish(self.root / "publication", "42", "v1.2.3")

    def test_publication_requires_an_existing_git_tag(self) -> None:
        self.mock_publication()
        with self.assertRaises(subprocess.CalledProcessError):
            publish(self.root / "publication", "42", "v9.9.9")
        self.assertEqual(self.registry_writes, [])

    def test_publication_rejects_chart_tampering_before_any_write(self) -> None:
        self.mock_publication()
        (self.base / self.release["chart"]["filename"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            publish(self.root / "publication", "42", "v1.2.3")
        self.assertEqual(self.registry_writes, [])

    def test_registry_inspection_distinguishes_missing_tags_from_failures(self) -> None:
        reference = REPOSITORIES["backend"] + ":v1.2.3"
        for error in ("unauthorized", "connection timed out", "invalid response"):
            with (
                patch(
                    "release.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 1, "", error),
                ),
                self.assertRaises(RuntimeError),
            ):
                registry_digest(reference, allow_missing=True)
        with patch(
            "release.subprocess.run",
            return_value=subprocess.CompletedProcess(
                [], 1, "", f"ERROR: {reference}: not found\n"
            ),
        ):
            self.assertIsNone(registry_digest(reference, allow_missing=True))
            with self.assertRaises(RuntimeError):
                registry_digest(reference)
        for output in ("[]", '{"digest":"latest"}'):
            with (
                patch(
                    "release.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0, output, ""),
                ),
                self.assertRaises(ValueError),
            ):
                registry_digest(reference)
        expected = "sha256:" + "a" * 64
        with patch(
            "release.subprocess.run",
            return_value=subprocess.CompletedProcess(
                [], 0, json.dumps({"digest": expected}), ""
            ),
        ):
            self.assertEqual(registry_digest(reference), expected)

    def test_duplicate_attempt_artifacts_fail_before_download(self) -> None:
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "neuro-inc/launchpad"}):
            with (
                patch("release.gh", return_value="2") as api,
                self.assertRaisesRegex(ValueError, "ambiguous release artifacts"),
            ):
                download_release(self.root / "download", "42")
            api.assert_called_once()

    def test_single_replacement_artifact_downloads(self) -> None:
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": "neuro-inc/launchpad"}),
            patch("release.gh", side_effect=["1\n0", ""]) as api,
        ):
            download_release(self.root / "download", "42")
        self.assertEqual(api.call_count, 2)
        self.assertNotIn("--slurp", api.call_args_list[0].args)
        self.assertEqual(api.call_args.args[:3], ("run", "download", "42"))

    def test_artifact_counts_cover_every_page_and_reject_invalid_counts(self) -> None:
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "neuro-inc/launchpad"}):
            for counts in ("1\n1", "2\n0", "1\n-1", "invalid", ""):
                with (
                    patch("release.gh", return_value=counts) as api,
                    self.assertRaises(ValueError),
                ):
                    download_release(self.root / "download", "42")
                api.assert_called_once()
            with (
                patch("release.gh", return_value="0\n0") as api,
                self.assertRaisesRegex(ValueError, "artifact is unavailable"),
            ):
                download_release(self.root / "download", "42")
            api.assert_called_once()

    def test_publication_requires_the_exact_commit_even_for_documentation(self) -> None:
        self.mock_publication()
        (self.root / "notes.txt").write_text("documentation only\n")
        self.commit()
        self.git("-c", "tag.gpgsign=false", "tag", "v1.2.4")
        with self.assertRaisesRegex(ValueError, "exact tagged commit"):
            publish(self.root / "publication", "42", "v1.2.4")
        self.assertEqual(self.registry_writes, [])

    def test_manifest_requires_all_three_immutable_images_from_the_expected_repositories(
        self,
    ) -> None:
        for reference in (
            "ghcr.io/neuro-inc/launchpad:master",
            "ghcr.io/other/launchpad@sha256:" + "a" * 64,
            "ghcr.io/neuro-inc/launchpad@sha256:invalid",
        ):
            with self.subTest(reference=reference):
                release = copy.deepcopy(self.release)
                release["images"]["backend"] = reference
                write_json(self.base / "release.json", release)
                with self.assertRaises(ValueError):
                    load_release(self.base)
        release = copy.deepcopy(self.release)
        del release["images"]["hook"]
        write_json(self.base / "release.json", release)
        with self.assertRaises(ValueError):
            load_release(self.base)

    def test_old_schema_and_mismatched_manifest_source_cannot_publish(self) -> None:
        self.mock_publication()
        for field, value in (("schema_version", 1), ("source_revision", "f" * 40)):
            with self.subTest(field=field):
                write_json(self.base / "release.json", {**self.release, field: value})
                with self.assertRaises(ValueError):
                    publish(self.root / "publication", "42", "v1.2.3")
                self.assertEqual(self.registry_writes, [])

    def test_complete_build_assembly_records_the_chart_and_exact_source(self) -> None:
        output = self.root / "output"
        assemble(output, self.images)
        release = verify_release(output, head())
        self.assertEqual(release["images"], self.images)
        self.assertEqual(release["source_revision"], head())
        self.assertEqual(release["schema_version"], 2)
        self.assertTrue((output / release["chart"]["filename"]).is_file())


if __name__ == "__main__":
    unittest.main()
