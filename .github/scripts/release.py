"""Assemble and publish one immutable Launchpad App release."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TypedDict


REPOSITORIES = {
    "backend": "ghcr.io/neuro-inc/launchpad",
    "frontend": "ghcr.io/neuro-inc/launchpad-web-ui",
    "hook": "ghcr.io/neuro-inc/launchpad-hook",
}
REVISION = r"[0-9a-f]{40}"
SHA256 = r"[0-9a-f]{64}"


class Chart(TypedDict):
    filename: str
    sha256: str


class Release(TypedDict):
    schema_version: int
    source_revision: str
    images: dict[str, str]
    chart: Chart


def fields(value: object, expected: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"The release must contain these fields: {sorted(expected)}.")
    return {str(key): item for key, item in value.items()}


def text(value: object, pattern: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError("The release contains an invalid identity.")
    return value


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True, timeout=60).strip()


def head() -> str:
    return text(command("git", "rev-parse", "HEAD"), REVISION)


def load_release(directory: Path) -> Release:
    value = fields(
        json.loads((directory / "release.json").read_text()),
        {"schema_version", "source_revision", "images", "chart"},
    )
    if type(value["schema_version"]) is not int or value["schema_version"] != 2:
        raise ValueError("The App release schema version is unsupported.")
    images = fields(value["images"], set(REPOSITORIES))
    chart = fields(value["chart"], {"filename", "sha256"})
    return {
        "schema_version": 2,
        "source_revision": text(value["source_revision"], REVISION),
        "images": {
            name: text(images[name], re.escape(repository) + "@sha256:" + SHA256)
            for name, repository in REPOSITORIES.items()
        },
        "chart": {
            "filename": text(chart["filename"], r"launchpad-[a-zA-Z0-9.+-]+\.tgz"),
            "sha256": text(chart["sha256"], SHA256),
        },
    }


def verify_release(directory: Path, revision: str) -> Release:
    release = load_release(directory)
    if release["source_revision"] != text(revision, REVISION):
        raise ValueError("The release does not match the tested source commit.")
    chart = release["chart"]
    archive = directory / chart["filename"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != chart["sha256"]:
        raise ValueError(
            "The chart archive checksum does not match the tested release."
        )
    return release


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def gh(*args: str) -> str:
    return command("gh", *args)


def download_release(directory: Path, run_id: str) -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    text(run_id, r"[1-9][0-9]*")
    page_counts = gh(
        "api",
        f"repos/{repository}/actions/runs/{run_id}/artifacts",
        "--paginate",
        "--jq",
        '[.artifacts[] | select(.name == "launchpad-release" and .expired == false)] | length',
    ).splitlines()
    if not page_counts:
        raise ValueError("The artifact API returned no page counts.")
    count = sum(int(text(value, r"0|[1-9][0-9]*")) for value in page_counts)
    if count == 0:
        raise ValueError("The selected App release artifact is unavailable.")
    if count != 1:
        raise ValueError("The workflow run has ambiguous release artifacts.")
    gh(
        "run",
        "download",
        run_id,
        "--repo",
        repository,
        "--name",
        "launchpad-release",
        "--dir",
        str(directory),
    )


def list_releases() -> list[dict[str, object]]:
    pages: object = json.loads(
        gh(
            "api",
            f"repos/{os.environ['GITHUB_REPOSITORY']}/releases?per_page=100",
            "--paginate",
            "--slurp",
        )
    )
    if not isinstance(pages, list):
        raise ValueError("GitHub must return release pages.")
    releases: list[dict[str, object]] = []
    for page in pages:
        if not isinstance(page, list):
            raise ValueError("GitHub must return a release list.")
        for item in page:
            if not isinstance(item, dict):
                raise ValueError("GitHub returned an invalid release.")
            releases.append({str(key): value for key, value in item.items()})
    return releases


def find_release(tag: str) -> dict[str, object] | None:
    matches = [release for release in list_releases() if release.get("tag_name") == tag]
    if len(matches) > 1:
        raise ValueError("GitHub returned duplicate releases for the tag.")
    return matches[0] if matches else None


def asset_names(release: dict[str, object]) -> set[str]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("GitHub Release assets must be a list.")
    names: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("name"), str):
            raise ValueError("GitHub returned an invalid release asset.")
        if asset["name"] in names:
            raise ValueError("GitHub returned duplicate release assets.")
        names.add(asset["name"])
    return names


def download_asset(tag: str, name: str, directory: Path) -> None:
    gh(
        "release",
        "download",
        tag,
        "--repo",
        os.environ["GITHUB_REPOSITORY"],
        "--pattern",
        name,
        "--dir",
        str(directory),
    )


def download_github_release(directory: Path, tag: str) -> bool:
    existing = find_release(tag)
    if existing is None or "release.json" not in asset_names(existing):
        return False
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        download_asset(tag, "release.json", staging)
        release = load_release(staging)
        chart = release["chart"]["filename"]
        if chart not in asset_names(existing):
            return False
        download_asset(tag, chart, staging)
        verify_release(staging, release["source_revision"])
        shutil.copytree(staging, directory, dirs_exist_ok=True)
    return True


def store_release_assets(directory: Path, tag: str) -> bool:
    release = load_release(directory)
    existing = find_release(tag)
    if existing is None:
        gh(
            "release",
            "create",
            tag,
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
            "--verify-tag",
            "--draft",
            "--title",
            tag,
            "--notes",
            "Publish the tested Launchpad App image and chart combination.",
        )
        existing = find_release(tag)
        if existing is None:
            raise ValueError("The draft GitHub Release was not created.")
    draft = existing.get("draft")
    if not isinstance(draft, bool):
        raise ValueError("GitHub returned an invalid release state.")
    names = asset_names(existing)
    for name in ("release.json", release["chart"]["filename"]):
        if name in names:
            with tempfile.TemporaryDirectory() as temporary:
                staging = Path(temporary)
                download_asset(tag, name, staging)
                if (staging / name).read_bytes() != (directory / name).read_bytes():
                    raise ValueError(f"The existing release asset conflicts: {name}.")
        else:
            if not draft:
                raise ValueError("The published GitHub Release is incomplete.")
            gh(
                "release",
                "upload",
                tag,
                str(directory / name),
                "--repo",
                os.environ["GITHUB_REPOSITORY"],
            )
    return draft


def registry_digest(reference: str, allow_missing: bool = False) -> str | None:
    result = subprocess.run(
        [
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            reference,
            "--format",
            "{{json .Manifest}}",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        if allow_missing and result.stderr.strip() == f"ERROR: {reference}: not found":
            return None
        raise RuntimeError(
            f"The registry could not verify {reference}: {result.stderr.strip()}"
        )
    manifest: object = json.loads(result.stdout)
    if not isinstance(manifest, dict):
        raise ValueError("The registry must return an image manifest descriptor.")
    return text(manifest.get("digest"), "sha256:" + SHA256)


def publish(directory: Path, run_id: str, release_tag: str) -> None:
    event = os.environ.get("GITHUB_EVENT_NAME")
    ref = os.environ.get("GITHUB_REF")
    manual = event == "workflow_dispatch" and ref == "refs/heads/master"
    tagged = event == "push" and ref == f"refs/tags/{release_tag}"
    if not (manual or tagged):
        raise ValueError("Publish from a version tag or dispatch Release from master.")
    text(release_tag, r"v[a-zA-Z0-9_.-]{0,127}")
    revision = text(
        command("git", "rev-parse", "--verify", f"refs/tags/{release_tag}^{{commit}}"),
        REVISION,
    )
    if download_github_release(directory, release_tag):
        release = verify_release(directory, revision)
    else:
        automatic = tagged
        if automatic:
            run_id = gh(
                "run",
                "list",
                "--repo",
                os.environ["GITHUB_REPOSITORY"],
                "--workflow",
                "ci.yaml",
                "--branch",
                "master",
                "--commit",
                revision,
                "--status",
                "success",
                "--limit",
                "20",
                "--json",
                "databaseId,event",
                "--jq",
                '[.[] | select(.event == "push" or .event == "workflow_dispatch")] | first | .databaseId // empty',
            )
            if not run_id:
                raise ValueError(
                    "Wait for successful master CI for the tagged commit, then rerun Release."
                )
        text(run_id, r"[1-9][0-9]*")
        run = fields(
            json.loads(
                gh(
                    "run",
                    "view",
                    run_id,
                    "--repo",
                    os.environ["GITHUB_REPOSITORY"],
                    "--json",
                    "conclusion,workflowName,headBranch,headSha,event",
                )
            ),
            {"conclusion", "workflowName", "headBranch", "headSha", "event"},
        )
        if (run["conclusion"], run["workflowName"], run["headBranch"]) != (
            "success",
            "CI",
            "master",
        ) or run["event"] not in ("push", "workflow_dispatch"):
            raise ValueError("The release requires a successful master CI run.")
        source = text(run["headSha"], REVISION)
        if source != revision:
            raise ValueError("Publication requires CI for the exact tagged commit.")
        download_release(directory, run_id)
        release = verify_release(directory, source)
    draft = store_release_assets(directory, release_tag)
    publish_aliases(release, release_tag)
    if draft:
        gh(
            "release",
            "edit",
            release_tag,
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
            "--draft=false",
        )


def publish_development(directory: Path) -> None:
    if (
        os.environ.get("GITHUB_EVENT_NAME") not in ("push", "workflow_dispatch")
        or os.environ.get("GITHUB_REF") != "refs/heads/master"
    ):
        raise ValueError("Development publication requires a master CI run.")
    source = head()
    release = verify_release(directory, source)
    current = text(
        gh(
            "api",
            f"repos/{os.environ['GITHUB_REPOSITORY']}/git/ref/heads/master",
            "--jq",
            ".object.sha",
        ),
        REVISION,
    )
    if source != current:
        raise ValueError("The development release no longer matches master.")
    publish_aliases(release, "master", replace=True)


def publish_aliases(release: Release, tag: str, *, replace: bool = False) -> None:
    aliases: list[tuple[str, str, str, bool]] = []
    for component in REPOSITORIES:
        reference = release["images"][component]
        expected = reference.split("@", 1)[1]
        if registry_digest(reference) != expected:
            raise ValueError("The registry image does not match the tested digest.")
        alias = REPOSITORIES[component] + ":" + tag
        existing = registry_digest(alias, allow_missing=True)
        if existing is not None and existing != expected and not replace:
            raise ValueError(
                f"The published version already selects a different image: {alias}."
            )
        aliases.append((alias, reference, expected, existing != expected))
    for alias, reference, expected, update in aliases:
        if update:
            command(
                "docker",
                "buildx",
                "imagetools",
                "create",
                "--prefer-index=false",
                "--tag",
                alias,
                reference,
            )
        if registry_digest(alias) != expected:
            raise ValueError(f"The published alias changed the tested digest: {alias}.")


def assemble(directory: Path, images: dict[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["helm", "package", "charts/launchpad", "--destination", str(directory)],
        check=True,
        timeout=60,
    )
    archives = list(directory.glob("launchpad-*.tgz"))
    if len(archives) != 1:
        raise ValueError("One packaged Launchpad chart is required.")
    release: Release = {
        "schema_version": 2,
        "source_revision": head(),
        "images": images,
        "chart": {
            "filename": archives[0].name,
            "sha256": hashlib.sha256(archives[0].read_bytes()).hexdigest(),
        },
    }
    write_json(directory / "release.json", release)
    verify_release(directory, head())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("assemble", "publish", "publish-development")
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--release-tag", default="")
    args = parser.parse_args()
    if args.operation == "assemble":
        assemble(
            args.directory,
            {name: os.environ[name.upper() + "_REF"] for name in REPOSITORIES},
        )
    elif args.operation == "publish-development":
        publish_development(args.directory)
    else:
        publish(args.directory, args.run_id, args.release_tag)


if __name__ == "__main__":
    main()
