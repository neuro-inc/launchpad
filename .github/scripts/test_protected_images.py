"""Test Launchpad release protection without registry mutations."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from protected_images import release_digests


class ProtectedImagesTests(unittest.TestCase):
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
                "protected_images.list_releases",
                return_value=[
                    {"tag_name": "v1.0", "assets": [{"name": "release.json"}]}
                ],
            ),
            patch("protected_images.download_asset", side_effect=download),
        ):
            protected = release_digests()
        for reference in images.values():
            repository, digest = reference.split("@")
            self.assertEqual(protected[repository], {digest})

    def test_release_api_failure_does_not_allow_cleanup(self) -> None:
        with (
            patch.dict("os.environ", {"GITHUB_REPOSITORY": "org/repo"}),
            patch(
                "protected_images.list_releases",
                side_effect=RuntimeError("unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            release_digests()

    def test_releases_without_manifests_keep_all_cleanup_targets(self) -> None:
        with patch("protected_images.list_releases", return_value=[{"assets": []}]):
            self.assertEqual(
                release_digests(),
                {
                    "ghcr.io/neuro-inc/launchpad": set(),
                    "ghcr.io/neuro-inc/launchpad-web-ui": set(),
                    "ghcr.io/neuro-inc/launchpad-hook": set(),
                },
            )


if __name__ == "__main__":
    unittest.main()
