"""Verify component reuse and assemble one immutable Launchpad release."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import TypedDict


REPOSITORIES = {
    "backend": "ghcr.io/neuro-inc/launchpad",
    "frontend": "ghcr.io/neuro-inc/launchpad-web-ui",
    "hook": "ghcr.io/neuro-inc/launchpad-hook",
}
BUILD_PATHS = {
    "backend": (
        "Dockerfile",
        ".dockerignore",
        "poetry.lock",
        "pyproject.toml",
        "Makefile",
        "README.md",
        ".apolo",
        "launchpad",
        "alembic.ini",
        "alembic",
        "scripts",
    ),
    "frontend": ("frontend",),
    "hook": (
        "hooks/hooks.Dockerfile",
        "hooks/poetry.lock",
        "hooks/pyproject.toml",
        ".apolo",
        "README.md",
        ".dockerignore",
        "Makefile",
    ),
    "chart": ("charts/launchpad", ".apolo/applications.yaml"),
}
COMMON_BUILD_PATHS = (
    ".github/workflows/ci.yaml",
    ".github/workflows/component-image.yml",
    ".github/workflows/release.yml",
    ".github/scripts",
)
REVISION = r"[0-9a-f]{40}"
SHA256 = r"[0-9a-f]{64}"


class Image(TypedDict):
    image_ref: str
    source_revision: str
    inputs_sha256: str


class Chart(TypedDict):
    filename: str
    sha256: str
    inputs_sha256: str


class Release(TypedDict):
    schema_version: int
    source_revision: str
    images: dict[str, Image]
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


def fingerprint(
    component: str, revision: str, dependencies: tuple[str, ...] = ()
) -> str:
    text(revision, REVISION)
    records = subprocess.check_output(
        [
            "git",
            "ls-tree",
            "-r",
            "-z",
            revision,
            "--",
            *BUILD_PATHS[component],
            *COMMON_BUILD_PATHS,
        ],
        timeout=60,
    )
    identity = json.dumps([component, dependencies], separators=(",", ":")).encode()
    return hashlib.sha256(identity + b"\0" + records).hexdigest()


def load_image(value: object, component: str) -> Image:
    record = fields(value, {"image_ref", "source_revision", "inputs_sha256"})
    return {
        "image_ref": text(
            record["image_ref"],
            re.escape(REPOSITORIES[component]) + "@sha256:" + SHA256,
        ),
        "source_revision": text(record["source_revision"], REVISION),
        "inputs_sha256": text(record["inputs_sha256"], SHA256),
    }


def load_release(directory: Path) -> Release:
    value = fields(
        json.loads((directory / "release.json").read_text()),
        {"schema_version", "source_revision", "images", "chart"},
    )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("The App release schema version is unsupported.")
    images = fields(value["images"], set(REPOSITORIES))
    chart = fields(value["chart"], {"filename", "sha256", "inputs_sha256"})
    return {
        "schema_version": 1,
        "source_revision": text(value["source_revision"], REVISION),
        "images": {name: load_image(record, name) for name, record in images.items()},
        "chart": {
            "filename": text(chart["filename"], r"launchpad-[a-zA-Z0-9.+-]+\.tgz"),
            "sha256": text(chart["sha256"], SHA256),
            "inputs_sha256": text(chart["inputs_sha256"], SHA256),
        },
    }


def hook_dependencies(images: dict[str, Image]) -> tuple[str, ...]:
    return tuple(images[name]["image_ref"] for name in ("backend", "frontend"))


def verify_release(directory: Path, revision: str | None = None) -> Release:
    release = load_release(directory)
    selected_revision = revision or release["source_revision"]
    for component, image in release["images"].items():
        dependencies = (
            hook_dependencies(release["images"]) if component == "hook" else ()
        )
        built_inputs = fingerprint(component, image["source_revision"], dependencies)
        selected_inputs = fingerprint(component, selected_revision, dependencies)
        if image["inputs_sha256"] != built_inputs or built_inputs != selected_inputs:
            raise ValueError(
                f"The {component} image does not match the selected build inputs."
            )
    chart = release["chart"]
    archive = directory / chart["filename"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != chart["sha256"]:
        raise ValueError(
            "The chart archive checksum does not match the tested release."
        )
    if fingerprint("chart", selected_revision) != chart["inputs_sha256"]:
        raise ValueError("The chart does not match the selected release inputs.")
    return release


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def gh(*args: str) -> str:
    return command("gh", *args)


def download_release(directory: Path, run_id: str, name: str) -> bool:
    repository = os.environ["GITHUB_REPOSITORY"]
    text(run_id, r"[1-9][0-9]*")
    page_counts = gh(
        "api",
        f"repos/{repository}/actions/runs/{run_id}/artifacts",
        "--paginate",
        "--jq",
        f'[.artifacts[] | select(.name == "{name}" and .expired == false)] | length',
    ).splitlines()
    if not page_counts:
        raise ValueError("The artifact API returned no page counts.")
    count = sum(int(text(value, r"0|[1-9][0-9]*")) for value in page_counts)
    if count == 0:
        return False
    if count != 1:
        raise ValueError("The workflow run has ambiguous release artifacts.")
    gh(
        "run",
        "download",
        run_id,
        "--repo",
        repository,
        "--name",
        name,
        "--dir",
        str(directory),
    )
    return True


def prepare(directory: Path, force: bool) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    repository = os.environ["GITHUB_REPOSITORY"]
    if os.environ["GITHUB_REF_TYPE"] == "tag":
        raise ValueError("Use the Release workflow to publish a version tag.")
    if not force:
        candidate = gh(
            "run",
            "list",
            "--repo",
            repository,
            "--workflow",
            "ci.yaml",
            "--branch",
            "master",
            "--status",
            "success",
            "--limit",
            "20",
            "--json",
            "databaseId,headSha,event",
            "--jq",
            '[.[] | select(.event == "push" or .event == "workflow_dispatch")] | first // empty',
        )
        if candidate:
            run = fields(json.loads(candidate), {"databaseId", "headSha", "event"})
            source = text(run["headSha"], REVISION)
            run_id = text(str(run["databaseId"]), r"[1-9][0-9]*")
            text(run["event"], r"push|workflow_dispatch")
            ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", source, "HEAD"], check=False
            ).returncode
            if ancestor not in (0, 1):
                raise ValueError("The reuse source commit is unavailable locally.")
            if ancestor == 0 and download_release(
                directory, run_id, "launchpad-release"
            ):
                release = verify_release(directory)
                if release["source_revision"] != source:
                    raise ValueError(
                        "The reuse artifact does not match its successful master run."
                    )
    if not (directory / "release.json").exists():
        (directory / "empty.txt").write_text("No reusable release is available.\n")


def select_image(
    component: str, directory: Path, dependencies: tuple[str, ...], force: bool
) -> Image | None:
    if not force and (directory / "release.json").exists():
        release = verify_release(directory)
        image = release["images"][component]
        if image["inputs_sha256"] == fingerprint(component, head(), dependencies):
            return image
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        raise ValueError("Production must reuse the complete tested App release.")
    return None


def outputs(values: dict[str, str]) -> None:
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in values.items()))


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
    if (
        os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_REF") != "refs/heads/master"
    ):
        raise ValueError(
            "Dispatch the Release workflow from master after development acceptance."
        )
    text(run_id, r"[1-9][0-9]*")
    text(release_tag, r"v[a-zA-Z0-9_.-]{0,127}")
    revision = text(
        command("git", "rev-parse", "--verify", f"refs/tags/{release_tag}^{{commit}}"),
        REVISION,
    )
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
    if not download_release(directory, run_id, "launchpad-release"):
        raise ValueError("The selected App release artifact is unavailable.")
    release = verify_release(directory)
    if release["source_revision"] != source:
        raise ValueError("The release does not match its successful master CI run.")
    verify_release(directory, revision)
    aliases: list[tuple[str, str, str, bool]] = []
    for component, image in release["images"].items():
        reference = image["image_ref"]
        expected = reference.split("@", 1)[1]
        if registry_digest(reference) != expected:
            raise ValueError("The registry image does not match the tested digest.")
        alias = REPOSITORIES[component] + ":" + release_tag
        existing = registry_digest(alias, allow_missing=True)
        if existing is not None and existing != expected:
            raise ValueError(
                f"The published version already selects a different image: {alias}."
            )
        aliases.append((alias, reference, expected, existing is None))
    for alias, reference, expected, missing in aliases:
        if missing:
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


def assemble(directory: Path, image_directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    images = {
        name: load_image(
            json.loads((image_directory / f"{name}.json").read_text()), name
        )
        for name in REPOSITORIES
    }
    subprocess.run(
        ["helm", "package", "charts/launchpad", "--destination", str(directory)],
        check=True,
        timeout=60,
    )
    archives = list(directory.glob("launchpad-*.tgz"))
    if len(archives) != 1:
        raise ValueError("One packaged Launchpad chart is required.")
    release = {
        "schema_version": 1,
        "source_revision": head(),
        "images": images,
        "chart": {
            "filename": archives[0].name,
            "sha256": hashlib.sha256(archives[0].read_bytes()).hexdigest(),
            "inputs_sha256": fingerprint("chart", head()),
        },
    }
    write_json(directory / "release.json", release)
    verify_release(directory)


def select_component(
    component: str, directory: Path, dependencies: tuple[str, ...], force: bool
) -> dict[str, str]:
    image = select_image(component, directory, dependencies, force)
    tag = os.environ["GITHUB_REF_NAME"]
    if component == "frontend":
        tag = head()
    elif os.environ["GITHUB_EVENT_NAME"] == "pull_request":
        tag = re.sub(r"[^a-z0-9_.-]", "-", os.environ["PR_BRANCH"].lower())
    elif os.environ["GITHUB_REF_TYPE"] != "tag":
        tag = "master"
    return {
        "build": str(image is None).lower(),
        "image_ref": image["image_ref"] if image else "",
        "tag": REPOSITORIES[component] + ":" + tag,
        "inputs_sha256": fingerprint(component, head(), dependencies),
        "context": "frontend" if component == "frontend" else ".",
        "dockerfile": {
            "backend": "Dockerfile",
            "frontend": "frontend/Dockerfile",
            "hook": "hooks/hooks.Dockerfile",
        }[component],
    }


def record_component(
    component: str,
    directory: Path,
    dependencies: tuple[str, ...],
    force: bool,
    digest: str,
) -> Image:
    image = select_image(component, directory, dependencies, force)
    if digest:
        image = {
            "image_ref": REPOSITORIES[component]
            + "@"
            + text(digest, "sha256:" + SHA256),
            "source_revision": head(),
            "inputs_sha256": fingerprint(component, head(), dependencies),
        }
    if image is None:
        raise ValueError("A successful build or verified reusable image is required.")
    write_json(Path(f"{component}.json"), image)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("prepare", "select", "record", "assemble", "publish"),
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--component", choices=tuple(REPOSITORIES))
    parser.add_argument("--digest", default="")
    parser.add_argument("--images", type=Path)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--release-tag", default="")
    args = parser.parse_args()
    force = os.environ.get("REBUILD_IMAGES") == "true"
    if args.operation == "prepare":
        prepare(args.directory, force)
    elif args.operation == "assemble":
        if args.images is None:
            parser.error("Release assembly requires image records.")
        assemble(args.directory, args.images)
    elif args.operation == "publish":
        publish(args.directory, args.run_id, args.release_tag)
    else:
        if args.component is None:
            parser.error("Component selection requires a component name.")
        component: str = args.component
        dependencies: tuple[str, ...] = ()
        if component == "hook":
            dependencies = tuple(
                os.environ[key] for key in ("BACKEND_REF", "FRONTEND_REF")
            )
            for name, value in zip(("backend", "frontend"), dependencies, strict=True):
                text(value, re.escape(REPOSITORIES[name]) + "@sha256:" + SHA256)
        if args.operation == "select":
            outputs(select_component(component, args.directory, dependencies, force))
        else:
            image = record_component(
                component, args.directory, dependencies, force, args.digest
            )
            outputs({"image_ref": image["image_ref"]})


if __name__ == "__main__":
    main()
