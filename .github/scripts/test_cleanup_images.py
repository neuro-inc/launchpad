"""Test image retention without deleting registry data."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cleanup_images import (
    Version,
    candidates,
    children,
    cleanup,
    package_versions,
    release_digests,
)


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        self.graph: dict[str, set[str]] = {}
        mocked = patch(
            "cleanup_images.children",
            side_effect=lambda repository, digest: self.graph.get(digest, set()),
        )
        mocked.start()
        self.addCleanup(mocked.stop)

    def version(self, number: int, tags: list[str], *, recent: bool = False) -> Version:
        return {
            "id": number,
            "digest": "sha256:" + f"{number:064x}",
            "tags": tags,
            "updated": self.cutoff + timedelta(days=1 if recent else -1),
        }

    def selected(
        self, versions: list[Version], published: set[str] | None = None
    ) -> list[int]:
        return [
            v["id"]
            for v in candidates("repository", versions, self.cutoff, published or set())
        ]

    def test_removes_only_expired_ci_versions_and_their_orphan_children(self) -> None:
        root = self.version(1, ["ci-" + "a" * 40])
        child = self.version(2, [])
        self.graph[root["digest"]] = {child["digest"]}
        self.assertEqual(self.selected([root, child, self.version(3, [])]), [1, 2])

    def test_partial_cleanup_can_resume_without_the_original_index(self) -> None:
        child = self.version(2, [], recent=True)
        child["tags"] = ["ci-gc-" + child["digest"].split(":", 1)[1]]
        self.assertEqual(self.selected([child]), [2])
        child["tags"].append("v1.0")
        self.assertEqual(self.selected([child]), [])

    def test_cleanup_deletes_nested_indexes_before_their_children(self) -> None:
        root = self.version(5, ["ci-" + "a" * 40])
        index = self.version(3, [])
        child = self.version(1, [])
        self.graph = {
            root["digest"]: {index["digest"]},
            index["digest"]: {child["digest"]},
        }
        self.assertEqual(self.selected([child, index, root]), [5, 3, 1])

    def test_manifest_cycle_aborts_before_deletion(self) -> None:
        root = self.version(1, ["ci-" + "a" * 40])
        child = self.version(2, [])
        self.graph = {
            root["digest"]: {child["digest"]},
            child["digest"]: {root["digest"]},
        }
        with self.assertRaisesRegex(ValueError, "manifest graph contains a cycle"):
            self.selected([root, child])

    def test_preserves_version_master_branch_unknown_and_recent_tags(self) -> None:
        for tag in ["v1.0", "master", "feature-test", "unknown", "a" * 40]:
            with self.subTest(tag=tag):
                self.assertEqual(self.selected([self.version(1, [tag])]), [])
                self.assertEqual(
                    self.selected([self.version(1, ["ci-" + "a" * 40, tag])]), []
                )
        self.assertEqual(
            self.selected([self.version(1, ["ci-" + "a" * 40], recent=True)]), []
        )

    def test_preserves_shared_children_of_published_nested_indexes(self) -> None:
        expired = self.version(1, ["ci-" + "a" * 40])
        published = self.version(2, ["v1.0"])
        index = self.version(3, [])
        child = self.version(4, [])
        self.graph = {
            expired["digest"]: {child["digest"]},
            published["digest"]: {index["digest"]},
            index["digest"]: {child["digest"]},
        }
        self.assertEqual(self.selected([expired, published, index, child]), [1])

    def test_release_manifest_protects_draft_or_published_digests(self) -> None:
        root = self.version(1, ["ci-" + "a" * 40])
        child = self.version(2, [])
        self.graph[root["digest"]] = {child["digest"]}
        self.assertEqual(self.selected([root, child], {root["digest"]}), [])

    def test_recent_untagged_child_remains(self) -> None:
        root = self.version(1, ["ci-" + "a" * 40])
        child = self.version(2, [], recent=True)
        self.graph[root["digest"]] = {child["digest"]}
        self.assertEqual(self.selected([root, child]), [])

    def test_retained_ci_graph_is_removed_after_its_last_child_expires(self) -> None:
        root = self.version(1, ["ci-" + "a" * 40])
        index = self.version(2, [])
        child = self.version(3, [], recent=True)
        expired_child = self.version(4, [])
        independent = self.version(5, ["ci-" + "b" * 40])
        unknown = self.version(6, [])
        self.graph = {
            root["digest"]: {index["digest"]},
            index["digest"]: {child["digest"], expired_child["digest"]},
            child["digest"]: set(),
            expired_child["digest"]: set(),
            independent["digest"]: set(),
            unknown["digest"]: set(),
        }
        versions = [root, index, child, expired_child, independent, unknown]

        with patch(
            "cleanup_images.children",
            side_effect=lambda repository, digest: self.graph[digest],
        ):
            first_pass = self.selected(versions)
            self.assertEqual(first_pass, [5])
            for version in versions:
                if version["id"] in first_pass:
                    del self.graph[version["digest"]]
            versions = [
                version for version in versions if version["id"] not in first_pass
            ]
            self.cutoff += timedelta(days=2)

            second_pass = self.selected(versions)
            self.assertEqual(second_pass[:2], [1, 2])
            self.assertCountEqual(second_pass[2:], [3, 4])

    def test_apply_marks_descendants_before_deleting_parents(self) -> None:
        root = self.version(1, ["ci-" + "a" * 40])
        child = self.version(2, [])
        self.graph[root["digest"]] = {child["digest"]}
        events: list[str] = []

        def mark(*args: str) -> str:
            events.append("mark")
            return ""

        def delete(*args: str) -> str:
            events.append(args[-1])
            return ""

        with (
            patch("cleanup_images.REPOSITORIES", {"backend": "ghcr.io/org/package"}),
            patch(
                "cleanup_images.release_digests",
                return_value={"ghcr.io/org/package": set()},
            ),
            patch("cleanup_images.package_versions", return_value=[root, child]),
            patch.dict("os.environ", {"GITHUB_REPOSITORY": "org/repo"}),
            patch(
                "cleanup_images.command",
                side_effect=mark,
            ),
            patch("cleanup_images.registry_digest", return_value=child["digest"]),
            patch(
                "cleanup_images.gh",
                side_effect=delete,
            ),
        ):
            cleanup(apply=True)
        self.assertEqual(
            events,
            [
                "mark",
                "orgs/org/packages/container/package/versions/1",
                "orgs/org/packages/container/package/versions/2",
            ],
        )

    def test_marker_failure_prevents_all_deletions(self) -> None:
        root = self.version(1, ["ci-" + "a" * 40])
        child = self.version(2, [])
        self.graph[root["digest"]] = {child["digest"]}
        with (
            patch("cleanup_images.REPOSITORIES", {"backend": "ghcr.io/org/package"}),
            patch(
                "cleanup_images.release_digests",
                return_value={"ghcr.io/org/package": set()},
            ),
            patch("cleanup_images.package_versions", return_value=[root, child]),
            patch.dict("os.environ", {"GITHUB_REPOSITORY": "org/repo"}),
            patch("cleanup_images.command", return_value=""),
            patch("cleanup_images.registry_digest", return_value="sha256:" + "f" * 64),
            patch("cleanup_images.gh") as api,
            self.assertRaisesRegex(ValueError, "marker"),
        ):
            cleanup(apply=True)
        api.assert_not_called()

    def test_registry_failure_aborts_before_any_deletion(self) -> None:
        with (
            patch(
                "cleanup_images.release_digests",
                return_value={"ghcr.io/neuro-inc/launchpad": set()},
            ),
            patch(
                "cleanup_images.package_versions",
                side_effect=RuntimeError("unavailable"),
            ),
            patch("cleanup_images.gh") as api,
            self.assertRaises(RuntimeError),
        ):
            cleanup(apply=True)
        api.assert_not_called()

    def test_dry_run_never_deletes(self) -> None:
        with (
            patch("cleanup_images.REPOSITORIES", {"backend": "ghcr.io/org/package"}),
            patch(
                "cleanup_images.release_digests",
                return_value={"ghcr.io/org/package": set()},
            ),
            patch(
                "cleanup_images.package_versions",
                return_value=[self.version(1, ["ci-" + "a" * 40])],
            ),
            patch.dict("os.environ", {"GITHUB_REPOSITORY": "org/repo"}),
            patch("cleanup_images.gh") as api,
        ):
            cleanup()
        api.assert_not_called()

    def test_package_pages_reject_invalid_metadata(self) -> None:
        with patch.dict("os.environ", {"GITHUB_REPOSITORY": "org/repo"}):
            for value in [{}, [{}], [[{"id": 1}]]]:
                with (
                    patch("cleanup_images.gh", return_value=json.dumps(value)),
                    self.assertRaises(ValueError),
                ):
                    package_versions("package")

    def test_invalid_manifest_aborts_cleanup(self) -> None:
        for value in [{}, {"schemaVersion": 2, "manifests": [{}]}]:
            with (
                patch("cleanup_images.command", return_value=json.dumps(value)),
                self.assertRaises(ValueError),
            ):
                children("repository", "sha256:" + "a" * 64)

    def test_manifest_assets_protect_all_component_digests(self) -> None:
        images = {
            "backend": "ghcr.io/neuro-inc/launchpad@sha256:" + "1" * 64,
            "frontend": "ghcr.io/neuro-inc/launchpad-web-ui@sha256:" + "2" * 64,
            "hook": "ghcr.io/neuro-inc/launchpad-hook@sha256:" + "3" * 64,
        }
        manifest = {
            "schema_version": 2,
            "source_revision": "a" * 40,
            "images": images,
            "chart": {"filename": "launchpad-1.0.0.tgz", "sha256": "b" * 64},
        }

        def download(tag: str, name: str, directory: Path) -> None:
            (directory / name).write_text(json.dumps(manifest))

        with (
            patch.dict("os.environ", {"GITHUB_REPOSITORY": "org/repo"}),
            patch(
                "cleanup_images.list_releases",
                return_value=[
                    {"tag_name": "v1.0", "assets": [{"name": "release.json"}]}
                ],
            ),
            patch("cleanup_images.download_asset", side_effect=download),
        ):
            protected = release_digests()
        for reference in images.values():
            repository, digest = reference.split("@")
            self.assertEqual(protected[repository], {digest})

    def test_later_package_failure_prevents_earlier_package_deletion(self) -> None:
        with (
            patch(
                "cleanup_images.REPOSITORIES",
                {"first": "ghcr.io/org/first", "second": "ghcr.io/org/second"},
            ),
            patch(
                "cleanup_images.release_digests",
                return_value={"ghcr.io/org/first": set(), "ghcr.io/org/second": set()},
            ),
            patch(
                "cleanup_images.package_versions",
                side_effect=[
                    [self.version(1, ["ci-" + "a" * 40])],
                    RuntimeError("unavailable"),
                ],
            ),
            patch("cleanup_images.gh") as api,
            self.assertRaises(RuntimeError),
        ):
            cleanup(apply=True)
        api.assert_not_called()

    def test_release_api_failure_does_not_allow_cleanup(self) -> None:
        with (
            patch.dict("os.environ", {"GITHUB_REPOSITORY": "org/repo"}),
            patch(
                "cleanup_images.list_releases", side_effect=RuntimeError("unavailable")
            ),
            self.assertRaises(RuntimeError),
        ):
            release_digests()
