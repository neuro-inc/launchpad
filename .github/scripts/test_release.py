"""Test component provenance, release assembly, and production promotion."""

import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from release import (
    REPOSITORIES,
    Image,
    Release,
    assemble,
    download_release,
    fingerprint,
    head,
    hook_dependencies,
    load_release,
    prepare,
    promote,
    record_component,
    select_component,
    select_image,
    verify_promotion,
    verify_release,
    write_json,
)
from rollout import runtime_resources, verify_deployment, verify_rollout


def argo_application(revision: str) -> dict[str, object]:
    return {
        "metadata": {"namespace": "argo"},
        "spec": {
            "sources": [
                {
                    "repoURL": "https://github.com/neuro-inc/launchpad",
                    "path": "charts/launchpad",
                }
            ]
        },
        "status": {
            "health": {"status": "Healthy"},
            "sync": {"status": "Synced", "revision": revision},
            "operationState": {
                "phase": "Succeeded",
                "syncResult": {"revision": revision},
            },
            "resources": [
                {
                    "group": "apps",
                    "kind": "Deployment",
                    "name": name,
                    "namespace": "app-project",
                }
                for name in ("launchpad-test", "launchpad-test-client")
            ],
        },
    }


def live_deployment(name: str, container: str, image: str) -> dict[str, object]:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "namespace": "app-project", "generation": 2},
        "spec": {
            "replicas": 1,
            "template": {"spec": {"containers": [{"name": container, "image": image}]}},
        },
        "status": {
            "observedGeneration": 2,
            "replicas": 1,
            "updatedReplicas": 1,
            "readyReplicas": 1,
            "availableReplicas": 1,
        },
    }


class ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(
            os.environ,
            {
                "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                "GITHUB_REF_TYPE": "branch",
                "GITHUB_REF_NAME": "master",
                "GITHUB_EVENT_NAME": "push",
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
        self.images: dict[str, Image] = {}
        for index, name in enumerate(REPOSITORIES):
            dependencies = hook_dependencies(self.images) if name == "hook" else ()
            self.images[name] = {
                "image_ref": REPOSITORIES[name] + "@sha256:" + str(index + 1) * 64,
                "source_revision": head(),
                "inputs_sha256": fingerprint(name, head(), dependencies),
            }
        archive = self.base / "launchpad-1.0.0.tgz"
        archive.write_bytes(b"chart archive")
        self.release: Release = {
            "schema_version": 1,
            "source_revision": head(),
            "images": self.images,
            "chart": {
                "filename": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "inputs_sha256": fingerprint("chart", head()),
            },
        }
        write_json(self.base / "release.json", self.release)
        write_json(
            self.base / "development-rollout.json",
            {
                "application": "dev-launchpad",
                "revision": "argo-revision",
                "release_sha256": hashlib.sha256(
                    (self.base / "release.json").read_bytes()
                ).hexdigest(),
                "images": [
                    self.images[name]["image_ref"] for name in ("backend", "frontend")
                ],
            },
        )

    def git(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.PIPE
        ).strip()

    def commit(self) -> None:
        self.git("add", ".")
        self.git("commit", "-qm", "test source")

    def change(self, path: str) -> None:
        (self.root / path).write_text("changed\n")
        # Release artifacts are outside the tracked build input paths.
        self.commit()

    def test_unchanged_components_reuse_verified_digests(self) -> None:
        verify_release(self.base)
        for component in REPOSITORIES:
            dependencies = hook_dependencies(self.images) if component == "hook" else ()
            self.assertEqual(
                select_image(component, self.base, dependencies, False),
                self.images[component],
            )

    def test_component_selection_preserves_publication_tags(self) -> None:
        cases = (
            ("backend", "pull_request", "branch", "feature", "feature-it-281-new"),
            ("backend", "push", "branch", "master", "master"),
            ("backend", "push", "tag", "v1.2.3", "v1.2.3"),
            ("frontend", "pull_request", "branch", "feature", head()),
        )
        for component, event, ref_type, ref_name, expected_tag in cases:
            with self.subTest(component=component, event=event, ref_type=ref_type):
                with patch.dict(
                    os.environ,
                    {
                        "GITHUB_EVENT_NAME": event,
                        "GITHUB_REF_TYPE": ref_type,
                        "GITHUB_REF_NAME": ref_name,
                        "PR_BRANCH": "Feature/IT-281 New",
                    },
                ):
                    selection = select_component(component, self.base, (), False)
                self.assertEqual(selection["build"], "false")
                self.assertEqual(
                    selection["tag"], REPOSITORIES[component] + ":" + expected_tag
                )
                self.assertEqual(
                    selection["image_ref"], self.images[component]["image_ref"]
                )

    def test_component_selection_identifies_a_required_frontend_build(self) -> None:
        self.change("frontend/src/app.ts")
        with patch.dict(
            os.environ, {"GITHUB_REF_TYPE": "branch", "GITHUB_REF_NAME": "master"}
        ):
            selection = select_component("frontend", self.base, (), False)
        self.assertEqual(selection["build"], "true")
        self.assertEqual(selection["image_ref"], "")
        self.assertEqual(selection["context"], "frontend")
        self.assertEqual(selection["dockerfile"], "frontend/Dockerfile")
        self.assertEqual(selection["inputs_sha256"], fingerprint("frontend", head()))

    def test_component_record_preserves_the_reused_source_identity(self) -> None:
        self.change("frontend/src/app.ts")
        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "branch"}):
            image = record_component("backend", self.base, (), False, "")
        self.assertEqual(image, self.images["backend"])
        self.assertNotEqual(image["source_revision"], head())
        self.assertEqual(json.loads(Path("backend.json").read_text()), image)

    def test_component_record_binds_a_new_build_to_its_source(self) -> None:
        self.change("launchpad/app.py")
        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "branch"}):
            image = record_component(
                "backend", self.base, (), True, "sha256:" + "a" * 64
            )
        self.assertEqual(
            image["image_ref"], REPOSITORIES["backend"] + "@sha256:" + "a" * 64
        )
        self.assertEqual(image["source_revision"], head())
        self.assertEqual(image["inputs_sha256"], fingerprint("backend", head()))
        self.assertEqual(json.loads(Path("backend.json").read_text()), image)

    def test_component_record_requires_a_build_digest_or_verified_reuse(self) -> None:
        for digest in ("", "latest", "sha256:invalid"):
            with self.subTest(digest=digest):
                with (
                    patch.dict(os.environ, {"GITHUB_REF_TYPE": "branch"}),
                    self.assertRaises(ValueError),
                ):
                    record_component("backend", self.base, (), True, digest)
                self.assertFalse(Path("backend.json").exists())

    def test_backend_change_preserves_frontend_reuse(self) -> None:
        self.change("launchpad/app.py")
        self.assertIsNone(select_image("backend", self.base, (), False))
        self.assertEqual(
            select_image("frontend", self.base, (), False), self.images["frontend"]
        )

    def test_frontend_change_preserves_backend_reuse(self) -> None:
        self.change("frontend/src/app.ts")
        self.assertIsNone(select_image("frontend", self.base, (), False))
        self.assertEqual(
            select_image("backend", self.base, (), False), self.images["backend"]
        )

    def test_hook_change_preserves_both_runtime_images(self) -> None:
        self.change("hooks/hooks.Dockerfile")
        for name in ("backend", "frontend"):
            self.assertEqual(
                select_image(name, self.base, (), False), self.images[name]
            )
        self.assertIsNone(
            select_image("hook", self.base, hook_dependencies(self.images), False)
        )

    def test_changed_runtime_digest_invalidates_hook(self) -> None:
        dependencies = (
            REPOSITORIES["backend"] + "@sha256:" + "a" * 64,
            self.images["frontend"]["image_ref"],
        )
        self.assertIsNone(select_image("hook", self.base, dependencies, False))

    def test_force_rebuild_does_not_reuse_images(self) -> None:
        for component in REPOSITORIES:
            dependencies = hook_dependencies(self.images) if component == "hook" else ()
            self.assertIsNone(select_image(component, self.base, dependencies, True))

    def test_tag_component_selection_never_requests_a_rebuild(self) -> None:
        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "tag"}):
            for component in REPOSITORIES:
                dependencies = (
                    hook_dependencies(self.images) if component == "hook" else ()
                )
                with (
                    self.subTest(component=component),
                    self.assertRaisesRegex(ValueError, "complete promoted App release"),
                ):
                    select_component(component, self.base, dependencies, True)

    def test_reuse_rejects_forged_source_fingerprint(self) -> None:
        release = copy.deepcopy(self.release)
        release["images"]["backend"]["inputs_sha256"] = "f" * 64
        write_json(self.base / "release.json", release)
        with self.assertRaisesRegex(ValueError, "backend image"):
            select_image("frontend", self.base, (), False)

    def test_reuse_rejects_mutable_or_wrong_repository_images(self) -> None:
        for image_ref in (
            REPOSITORIES["frontend"] + ":master",
            REPOSITORIES["backend"] + "@sha256:" + "a" * 64,
        ):
            release = copy.deepcopy(self.release)
            release["images"]["frontend"]["image_ref"] = image_ref
            write_json(self.base / "release.json", release)
            with self.assertRaises(ValueError):
                load_release(self.base)

    def test_chart_change_reuses_images_but_rejects_old_promotion(self) -> None:
        self.change("charts/launchpad/values.yaml")
        for component in REPOSITORIES:
            dependencies = hook_dependencies(self.images) if component == "hook" else ()
            self.assertEqual(
                select_image(component, self.base, dependencies, False),
                self.images[component],
            )
        with self.assertRaisesRegex(ValueError, "chart"):
            verify_promotion(self.base, head())

    def test_promotion_allows_new_commit_with_identical_build_inputs(self) -> None:
        (self.root / "notes.txt").write_text("documentation only\n")
        self.commit()
        self.assertNotEqual(head(), self.release["source_revision"])
        self.assertEqual(verify_promotion(self.base, head()), self.release)

    def test_promotion_rejects_changed_component_inputs(self) -> None:
        self.change("frontend/src/app.ts")
        with self.assertRaisesRegex(ValueError, "frontend image"):
            verify_promotion(self.base, head())

    def test_promotion_rejects_missing_or_tampered_evidence(self) -> None:
        path = self.base / "development-rollout.json"
        evidence = json.loads(path.read_text())
        for key in ("release_sha256", "images", "application", "revision"):
            invalid = {**evidence, key: ""}
            write_json(path, invalid)
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_promotion(self.base, head())

    def test_chart_checksum_and_path_are_validated(self) -> None:
        (self.base / "launchpad-1.0.0.tgz").write_bytes(b"tampered archive")
        with self.assertRaisesRegex(ValueError, "checksum"):
            verify_release(self.base)
        release = copy.deepcopy(self.release)
        release["chart"]["filename"] = "../launchpad-1.0.0.tgz"
        write_json(self.base / "release.json", release)
        with self.assertRaises(ValueError):
            load_release(self.base)

    def test_production_assembly_preserves_the_promoted_bytes(self) -> None:
        records = self.root / "images"
        records.mkdir()
        for name, image in self.images.items():
            write_json(records / f"{name}.json", image)
        output = self.root / "output"
        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "tag"}):
            assemble(output, records, self.base)
        for name in ("release.json", "development-rollout.json", "launchpad-1.0.0.tgz"):
            self.assertEqual(
                (output / name).read_bytes(), (self.base / name).read_bytes()
            )

    def test_production_assembly_rejects_a_different_image_combination(self) -> None:
        records = self.root / "images"
        records.mkdir()
        for name, image in self.images.items():
            record = {**image, "image_ref": REPOSITORIES[name] + "@sha256:" + "f" * 64}
            write_json(records / f"{name}.json", record)
        with (
            patch.dict(os.environ, {"GITHUB_REF_TYPE": "tag"}),
            self.assertRaises(ValueError),
        ):
            assemble(self.root / "output", records, self.base)

    def test_tag_dispatch_requires_an_explicit_verified_promotion(self) -> None:
        destination = self.root / "production-base"

        def download(directory: Path, run_id: str, name: str) -> bool:
            self.assertEqual(run_id, "42")
            self.assertEqual(name, "launchpad-production-release")
            shutil.copytree(self.base, directory, dirs_exist_ok=True)
            return True

        with (
            patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                    "GITHUB_REF_TYPE": "tag",
                    "GITHUB_REF_NAME": "v1.2.3",
                    "GITHUB_EVENT_NAME": "workflow_dispatch",
                },
            ),
            patch("release.gh", return_value="") as api,
            patch("release.download_release", side_effect=download),
        ):
            prepare(destination, False, "42")
        self.assertEqual(api.call_args.args[:3], ("run", "view", "42"))
        self.assertEqual(verify_promotion(destination, head()), self.release)

    def test_tag_dispatch_rejects_invalid_release_inputs_before_network_access(
        self,
    ) -> None:
        cases = (
            ("push", "v1.2.3", False, "42"),
            ("workflow_dispatch", "release", False, "42"),
            ("workflow_dispatch", "v1.2.3", True, "42"),
            ("workflow_dispatch", "v1.2.3", False, ""),
            ("workflow_dispatch", "v1.2.3", False, "0"),
            ("workflow_dispatch", "v1.2.3", False, "invalid"),
        )
        for event, ref_name, force, run_id in cases:
            with self.subTest(
                event=event, ref_name=ref_name, force=force, run_id=run_id
            ):
                with (
                    patch.dict(
                        os.environ,
                        {
                            "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                            "GITHUB_REF_TYPE": "tag",
                            "GITHUB_REF_NAME": ref_name,
                            "GITHUB_EVENT_NAME": event,
                        },
                    ),
                    patch("release.gh") as api,
                    self.assertRaises(ValueError),
                ):
                    prepare(self.root / "candidate", force, run_id)
                api.assert_not_called()

    def test_development_dispatch_rejects_a_production_release_selection(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                    "GITHUB_REF_TYPE": "branch",
                },
            ),
            patch("release.gh") as api,
            self.assertRaisesRegex(ValueError, "only for a version tag"),
        ):
            prepare(self.root / "candidate", False, "42")
        api.assert_not_called()

    def test_tag_dispatch_rejects_unavailable_or_failed_promotions(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                "GITHUB_REF_TYPE": "tag",
                "GITHUB_REF_NAME": "v1.2.3",
                "GITHUB_EVENT_NAME": "workflow_dispatch",
            },
        ):
            with (
                patch(
                    "release.gh", side_effect=subprocess.CalledProcessError(1, ["gh"])
                ),
                patch("release.download_release") as download,
                self.assertRaises(subprocess.CalledProcessError),
            ):
                prepare(self.root / "candidate", False, "42")
            download.assert_not_called()
            with (
                patch("release.gh", return_value=""),
                patch("release.download_release", return_value=False),
                self.assertRaisesRegex(ValueError, "artifact is unavailable"),
            ):
                prepare(self.root / "candidate", False, "42")

    def test_empty_or_forced_reuse_base_builds_fresh(self) -> None:
        for force in (False, True):
            directory = self.root / str(force)
            with patch.dict(
                os.environ,
                {
                    "GITHUB_REPOSITORY": "neuro-inc/launchpad",
                    "GITHUB_REF_TYPE": "branch",
                },
            ):
                with patch("release.gh", return_value="") as api:
                    prepare(directory, force)
            self.assertTrue((directory / "empty.txt").exists())
            if force:
                api.assert_not_called()
            self.assertIsNone(select_image("backend", directory, (), False))

    def test_reuse_base_requires_the_successful_runs_source_identity(self) -> None:
        self.change("frontend/src/app.ts")
        candidate = json.dumps({"databaseId": 42, "headSha": head(), "event": "push"})
        destination = self.root / "candidate"

        def api(*args: str) -> str:
            if args[:2] == ("run", "list"):
                return candidate
            if args[0] == "api":
                return "1"
            shutil.copytree(self.base, destination, dirs_exist_ok=True)
            return ""

        with patch.dict(
            os.environ,
            {"GITHUB_REPOSITORY": "neuro-inc/launchpad", "GITHUB_REF_TYPE": "branch"},
        ):
            with (
                patch("release.gh", side_effect=api),
                self.assertRaisesRegex(ValueError, "successful master run"),
            ):
                prepare(destination, False)

    def test_duplicate_attempt_artifacts_fail_before_download(self) -> None:
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "neuro-inc/launchpad"}):
            for name in ("launchpad-release", "launchpad-production-release"):
                with (
                    patch("release.gh", return_value="2") as api,
                    self.assertRaisesRegex(ValueError, "ambiguous release artifacts"),
                ):
                    download_release(self.root / "download", "42", name)
                api.assert_called_once()

    def test_single_replacement_artifact_downloads(self) -> None:
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": "neuro-inc/launchpad"}),
            patch("release.gh", side_effect=["1\n0", ""]) as api,
        ):
            self.assertTrue(
                download_release(self.root / "download", "42", "launchpad-release")
            )
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
                    download_release(self.root / "download", "42", "launchpad-release")
                api.assert_called_once()
            with patch("release.gh", return_value="0\n0") as api:
                self.assertFalse(
                    download_release(self.root / "download", "42", "launchpad-release")
                )
                api.assert_called_once()

    def test_development_assembly_rejects_a_hook_for_different_runtime_images(
        self,
    ) -> None:
        records = self.root / "records"
        records.mkdir()
        for name, image in self.images.items():
            record = dict(image)
            if name == "backend":
                record["image_ref"] = REPOSITORIES[name] + "@sha256:" + "f" * 64
            write_json(records / f"{name}.json", record)

        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "branch"}):
            with self.assertRaisesRegex(ValueError, "hook image"):
                assemble(self.root / "output", records, self.base)

    def test_development_assembly_keeps_verified_reused_records(self) -> None:
        records = self.root / "records"
        records.mkdir()
        for name, image in self.images.items():
            write_json(records / f"{name}.json", image)

        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "branch"}):
            assemble(self.root / "output", records, self.base)
        self.assertEqual(verify_release(self.root / "output")["images"], self.images)

    def test_promotion_binds_the_running_pair_and_deployed_chart(self) -> None:
        application = argo_application(head())
        backend = live_deployment(
            "launchpad-test", "launchpad", self.images["backend"]["image_ref"]
        )
        frontend = live_deployment(
            "launchpad-test-client", "frontend", self.images["frontend"]["image_ref"]
        )

        def responses() -> list[io.StringIO]:
            return [
                io.StringIO(json.dumps(application)),
                io.StringIO(json.dumps({"manifest": json.dumps(backend)})),
                io.StringIO(json.dumps({"manifest": json.dumps(frontend)})),
            ]

        environment = {
            "ARGOCD_SERVER": "https://argo.example.invalid",
            "DEV_LAUNCHPAD_ARGO_APPLICATION": "dev-launchpad",
            "ARGOCD_AUTH_TOKEN": "synthetic-test-token",
        }
        with patch.dict(os.environ, environment):
            with patch(
                "release.urllib.request.urlopen",
                side_effect=responses(),
            ) as api:
                promote(self.base, self.release["source_revision"])
        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(api.call_args_list[1].args[0].full_url).query
        )
        self.assertEqual(
            query,
            {
                "appNamespace": ["argo"],
                "namespace": ["app-project"],
                "resourceName": ["launchpad-test"],
                "group": ["apps"],
                "version": ["v1"],
                "kind": ["Deployment"],
            },
        )
        self.assertEqual(verify_promotion(self.base, head()), self.release)
        status = application["status"]
        assert isinstance(status, dict)
        for wrong_image in (
            REPOSITORIES["frontend"] + "@sha256:" + "f" * 64,
            "unrelated.example/frontend@sha256:" + "f" * 64,
        ):
            status["summary"] = {
                "images": [
                    self.images[name]["image_ref"] for name in ("backend", "frontend")
                ]
                + [wrong_image]
            }
            frontend = live_deployment("launchpad-test-client", "frontend", wrong_image)
            with (
                patch.dict(os.environ, environment),
                patch("release.urllib.request.urlopen", side_effect=responses()),
                self.assertRaisesRegex(ValueError, "live Deployment does not run"),
            ):
                promote(self.base, self.release["source_revision"])
        frontend = live_deployment(
            "launchpad-test-client", "frontend", self.images["frontend"]["image_ref"]
        )
        self.change("charts/launchpad/values.yaml")
        status = application["status"]
        assert isinstance(status, dict)
        status["sync"]["revision"] = head()
        status["operationState"]["syncResult"]["revision"] = head()
        with patch.dict(os.environ, environment):
            with patch(
                "release.urllib.request.urlopen",
                side_effect=responses(),
            ):
                with self.assertRaisesRegex(ValueError, "deployed chart"):
                    promote(self.base, self.release["source_revision"])


class RolloutTests(unittest.TestCase):
    def application(self) -> dict[str, object]:
        return argo_application("selected")

    def test_rollout_requires_health_and_the_completed_revision(self) -> None:
        self.assertEqual(verify_rollout(self.application()), "selected")
        for section, key, value in (
            ("health", "status", "Degraded"),
            ("sync", "status", "OutOfSync"),
            ("operationState", "phase", "Running"),
        ):
            application = self.application()
            status = application["status"]
            assert isinstance(status, dict)
            status[section][key] = value
            with self.assertRaises(ValueError):
                verify_rollout(application)
        application = self.application()
        status = application["status"]
        assert isinstance(status, dict)
        status["operationState"]["syncResult"]["revision"] = "stale"
        with self.assertRaises(ValueError):
            verify_rollout(application)

    def test_multisource_rollout_selects_the_chart_revision_and_checks_all_sources(
        self,
    ) -> None:
        application = self.application()
        application["spec"] = {
            "sources": [
                {
                    "repoURL": "https://github.com/neuro-inc/app-types.git",
                    "path": "charts/hook",
                },
                {
                    "repoURL": "https://github.com/neuro-inc/launchpad.git",
                    "path": "charts/launchpad",
                },
            ]
        }
        status = application["status"]
        assert isinstance(status, dict)
        status["sync"] = {
            "status": "Synced",
            "revisions": ["hook-revision", "chart-revision"],
        }
        status["operationState"] = {
            "phase": "Succeeded",
            "syncResult": {"revisions": ["hook-revision", "chart-revision"]},
        }
        self.assertEqual(verify_rollout(application), "chart-revision")
        status["operationState"]["syncResult"]["revisions"][0] = "stale-hook-revision"
        with self.assertRaises(ValueError):
            verify_rollout(application)

    def test_rollout_rejects_missing_or_ambiguous_chart_sources(self) -> None:
        for sources in (
            [],
            [{"repoURL": "https://example.invalid", "path": "charts/launchpad"}],
            [
                {
                    "repoURL": "https://github.com/neuro-inc/launchpad",
                    "path": "charts/launchpad",
                }
            ]
            * 2,
        ):
            application = self.application()
            application["spec"] = {"sources": sources}
            with self.assertRaises(ValueError):
                verify_rollout(application)

    def test_rollout_rejects_malformed_objects(self) -> None:
        for path in (
            ("status",),
            ("status", "health"),
            ("status", "sync"),
            ("status", "operationState"),
            ("status", "operationState", "syncResult"),
        ):
            invalid_values: tuple[object, ...] = (None, [], "invalid")
            for value in invalid_values:
                application = self.application()
                parent: object = application
                for key in path[:-1]:
                    assert isinstance(parent, dict)
                    parent = parent[key]
                assert isinstance(parent, dict)
                parent[path[-1]] = value
                with self.assertRaises(ValueError):
                    verify_rollout(application)

    def test_runtime_resources_reject_missing_or_ambiguous_pairs(self) -> None:
        application = self.application()
        expected = runtime_resources(application)
        self.assertEqual(expected[0]["name"], "launchpad-test")
        self.assertEqual(expected[1]["name"], "launchpad-test-client")
        self.assertEqual(expected[0]["app_namespace"], "argo")
        status = application["status"]
        assert isinstance(status, dict)
        original = status["resources"]
        assert isinstance(original, list)
        for resources in (None, [], original[:1], original * 2, [None]):
            status["resources"] = resources
            with self.assertRaises(ValueError):
                runtime_resources(application)

    def test_live_deployment_requires_exact_image_and_completed_generation(
        self,
    ) -> None:
        for resource, container in zip(
            runtime_resources(self.application()),
            ("launchpad", "frontend"),
            strict=True,
        ):
            deployment = live_deployment(
                resource["name"], container, "selected@sha256:digest"
            )
            verify_deployment(deployment, resource, container, "selected@sha256:digest")
            with self.assertRaisesRegex(ValueError, "runtime image"):
                verify_deployment(
                    deployment, resource, container, "different@sha256:digest"
                )
            for section, key, value in (
                ("metadata", "generation", 3),
                ("metadata", "deletionTimestamp", "2026-01-01T00:00:00Z"),
                ("metadata", "namespace", "wrong-project"),
                ("metadata", "name", "historical-deployment"),
                ("spec", "replicas", 0),
                ("spec", "paused", True),
                ("status", "observedGeneration", 1),
                ("status", "replicas", 2),
                ("status", "updatedReplicas", 0),
                ("status", "readyReplicas", 0),
                ("status", "availableReplicas", 0),
                ("status", "unavailableReplicas", 1),
                ("status", "observedGeneration", True),
            ):
                changed = copy.deepcopy(deployment)
                parent = changed[section]
                assert isinstance(parent, dict)
                parent[key] = value
                with self.assertRaises(ValueError):
                    verify_deployment(
                        changed, resource, container, "selected@sha256:digest"
                    )
            for section in ("metadata", "spec", "status"):
                changed = copy.deepcopy(deployment)
                changed[section] = []
                with self.assertRaises(ValueError):
                    verify_deployment(
                        changed, resource, container, "selected@sha256:digest"
                    )


if __name__ == "__main__":
    unittest.main()
