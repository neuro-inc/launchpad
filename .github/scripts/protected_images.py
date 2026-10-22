"""Collect the image digests protected by Launchpad release manifests."""

import argparse
import tempfile
from pathlib import Path

from release import (
    REPOSITORIES,
    asset_names,
    download_asset,
    list_releases,
    load_release,
    text,
    write_json,
)


def release_digests() -> dict[str, set[str]]:
    protected = {repository: set[str]() for repository in REPOSITORIES.values()}
    for existing in list_releases():
        if "release.json" not in asset_names(existing):
            continue
        tag = text(existing.get("tag_name"), r"v[a-zA-Z0-9_.-]{0,127}")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            download_asset(tag, "release.json", directory)
            release = load_release(directory)
        for name, reference in release["images"].items():
            protected[REPOSITORIES[name]].add(reference.split("@", 1)[1])
    return protected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_json(
        args.output,
        {
            repository: sorted(digests)
            for repository, digests in release_digests().items()
        },
    )
