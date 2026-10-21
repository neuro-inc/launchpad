"""Remove expired CI image versions while preserving published image graphs."""

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote

from release import (
    REPOSITORIES,
    SHA256,
    asset_names,
    command,
    download_asset,
    gh,
    list_releases,
    load_release,
    registry_digest,
    text,
)


class Version(TypedDict):
    id: int
    digest: str
    tags: list[str]
    updated: datetime


def package_versions(package: str) -> list[Version]:
    owner = os.environ["GITHUB_REPOSITORY"].split("/", 1)[0]
    pages: object = json.loads(
        gh(
            "api",
            f"orgs/{owner}/packages/container/{quote(package, safe='')}/versions?per_page=100",
            "--paginate",
            "--slurp",
        )
    )
    if not isinstance(pages, list):
        raise ValueError("GitHub must return package version pages.")
    versions: list[Version] = []
    for page in pages:
        if not isinstance(page, list):
            raise ValueError("GitHub must return a package version list.")
        for item in page:
            if (
                not isinstance(item, dict)
                or type(item.get("id")) is not int
                or item["id"] <= 0
            ):
                raise ValueError("GitHub returned an invalid package version.")
            metadata = item.get("metadata")
            container = (
                metadata.get("container") if isinstance(metadata, dict) else None
            )
            tags = container.get("tags") if isinstance(container, dict) else None
            if not isinstance(tags, list) or not all(
                isinstance(tag, str) for tag in tags
            ):
                raise ValueError("GitHub returned invalid container tags.")
            updated = item.get("updated_at")
            if not isinstance(updated, str):
                raise ValueError("GitHub returned an invalid package timestamp.")
            timestamp = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("Package timestamps must include a timezone.")
            versions.append(
                {
                    "id": item["id"],
                    "digest": text(item.get("name"), "sha256:" + SHA256),
                    "tags": tags,
                    "updated": timestamp,
                }
            )
    if len({v["digest"] for v in versions}) != len(versions):
        raise ValueError("GitHub returned duplicate image digests.")
    return versions


def children(repository: str, digest: str) -> set[str]:
    manifest: object = json.loads(
        command(
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            "--raw",
            repository + "@" + digest,
        )
    )
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 2:
        raise ValueError("The registry returned an unsupported manifest.")
    descriptors = manifest.get("manifests")
    if descriptors is None:
        if not isinstance(manifest.get("config"), dict) or not isinstance(
            manifest.get("layers"), list
        ):
            raise ValueError("The registry returned an invalid image manifest.")
        return set()
    if not isinstance(descriptors, list):
        raise ValueError("The registry returned an invalid image index.")
    result: set[str] = set()
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError("The image index contains an invalid descriptor.")
        result.add(text(descriptor.get("digest"), "sha256:" + SHA256))
    return result


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


def candidates(
    repository: str, versions: list[Version], cutoff: datetime, published: set[str]
) -> list[Version]:
    marked = {
        v["digest"]
        for v in versions
        if "ci-gc-" + v["digest"].split(":", 1)[1] in v["tags"]
    }
    expired = {v["digest"] for v in versions if v["updated"] < cutoff} | marked
    roots = {
        v["digest"]
        for v in versions
        if v["digest"] in expired
        and v["tags"]
        and all(
            re.fullmatch(r"ci-[0-9a-f]{40}", tag)
            or tag == "ci-gc-" + v["digest"].split(":", 1)[1]
            for tag in v["tags"]
        )
    }
    if not roots:
        return []
    graph: dict[str, set[str]] = {}

    def reachable(seeds: set[str]) -> set[str]:
        seen: set[str] = set()
        pending = list(seeds)
        while pending:
            digest = pending.pop()
            if digest in seen:
                continue
            seen.add(digest)
            if digest not in graph:
                graph[digest] = children(repository, digest)
            pending.extend(graph[digest] - seen)
        return seen

    temporary = reachable(roots)
    eligible = {
        v["digest"]
        for v in versions
        if v["digest"] in temporary & expired
        and (v["digest"] in roots or not v["tags"])
    }
    protected = reachable(
        published | {v["digest"] for v in versions if v["digest"] not in eligible}
    )
    remaining = {
        v["digest"]: v for v in versions if v["digest"] in eligible - protected
    }
    try:
        child_first = tuple(
            TopologicalSorter(
                {digest: graph[digest] & remaining.keys() for digest in remaining}
            ).static_order()
        )
    except CycleError as error:
        raise ValueError("The image manifest graph contains a cycle.") from error

    # CI ancestors retain ownership of untagged children until those children expire.
    retained = {
        v["digest"] for v in versions if not v["tags"] and v["digest"] not in expired
    }
    for digest in child_first:
        if graph[digest] & retained:
            retained.add(digest)
    retained = reachable(retained)
    return [
        remaining[digest] for digest in reversed(child_first) if digest not in retained
    ]


def cleanup(*, apply: bool = False) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    published = release_digests()
    planned: list[tuple[str, list[Version]]] = []
    for repository in REPOSITORIES.values():
        package = repository.rsplit("/", 1)[1]
        planned.append(
            (
                package,
                candidates(
                    repository, package_versions(package), cutoff, published[repository]
                ),
            )
        )
    if apply:
        # Preserve cleanup ownership before deleting indexes that identify their children.
        for package, versions in planned:
            for version in versions:
                if not version["tags"]:
                    reference = f"ghcr.io/{os.environ['GITHUB_REPOSITORY'].split('/', 1)[0]}/{package}@{version['digest']}"
                    marker = (
                        reference.split("@", 1)[0]
                        + ":ci-gc-"
                        + version["digest"].split(":", 1)[1]
                    )
                    command(
                        "docker",
                        "buildx",
                        "imagetools",
                        "create",
                        "--prefer-index=false",
                        "--tag",
                        marker,
                        reference,
                    )
                    if registry_digest(marker) != version["digest"]:
                        raise ValueError("The cleanup marker changed the image digest.")
    owner = os.environ["GITHUB_REPOSITORY"].split("/", 1)[0]
    for package, versions in planned:
        for version in versions:
            print(
                f"{'Delete' if apply else 'Would delete'} {package}@{version['digest']}",
                flush=True,
            )
            if apply:
                # Publication and cleanup share a workflow concurrency group.
                gh(
                    "api",
                    "--method",
                    "DELETE",
                    f"orgs/{owner}/packages/container/{quote(package, safe='')}/versions/{version['id']}",
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    cleanup(apply=parser.parse_args().apply)
