"""Verify component reuse and assemble one immutable Launchpad release."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TypedDict

from rollout import runtime_resources, verify_deployment, verify_rollout


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


def verify_promotion(directory: Path, revision: str) -> Release:
    release = verify_release(directory, revision)
    evidence = fields(
        json.loads((directory / "development-rollout.json").read_text()),
        {"application", "revision", "release_sha256", "images"},
    )
    text(evidence["application"], r"[^\s]+")
    text(evidence["revision"], r"[^\s]+")
    checksum = hashlib.sha256((directory / "release.json").read_bytes()).hexdigest()
    images = [release["images"][name]["image_ref"] for name in ("backend", "frontend")]
    if evidence["release_sha256"] != checksum or evidence["images"] != images:
        raise ValueError(
            "The development rollout does not bind the complete App release."
        )
    return release


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
        run_id = os.environ["APP_RELEASE_RUN_ID"]
        gh(
            "run",
            "view",
            run_id,
            "--repo",
            repository,
            "--json",
            "conclusion,workflowName,headBranch,event",
            "--jq",
            'if .conclusion == "success" and .workflowName == "Verify production App promotion" and .headBranch == "master" and .event == "workflow_dispatch" then . else error("Verified App promotion is required.") end',
        )
        if not download_release(directory, run_id, "launchpad-production-release"):
            raise ValueError("The verified App promotion artifact is unavailable.")
        verify_promotion(directory, head())
    elif not force:
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
        raise ValueError("Production must reuse the complete promoted App release.")
    return None


def outputs(values: dict[str, str]) -> None:
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in values.items()))


def promote(directory: Path, expected_revision: str) -> None:
    release = verify_release(directory)
    if release["source_revision"] != text(expected_revision, REVISION):
        raise ValueError("The release does not match its successful master CI run.")
    server = os.environ["ARGOCD_SERVER"].rstrip("/")
    if urllib.parse.urlparse(server).scheme != "https":
        raise ValueError("ARGOCD_SERVER must use HTTPS.")
    name = os.environ["DEV_LAUNCHPAD_ARGO_APPLICATION"]
    base_url = f"{server}/api/v1/applications/{urllib.parse.quote(name, safe='')}"

    def read_argo(suffix: str) -> object:
        request = urllib.request.Request(
            base_url + suffix,
            headers={"Authorization": "Bearer " + os.environ["ARGOCD_AUTH_TOKEN"]},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    application = read_argo("")
    images = tuple(
        release["images"][name]["image_ref"] for name in ("backend", "frontend")
    )
    revision = verify_rollout(application)
    if (
        fingerprint("chart", text(revision, REVISION))
        != release["chart"]["inputs_sha256"]
    ):
        raise ValueError("The deployed chart does not match the selected App release.")
    for resource, container, image in zip(
        runtime_resources(application), ("launchpad", "frontend"), images, strict=True
    ):
        query = urllib.parse.urlencode(
            {
                "appNamespace": resource["app_namespace"],
                "namespace": resource["namespace"],
                "resourceName": resource["name"],
                "version": "v1",
                "kind": "Deployment",
                "group": "apps",
            }
        )
        response = fields(read_argo("/resource?" + query), {"manifest"})
        deployment = json.loads(text(response["manifest"], r"(?s).+"))
        verify_deployment(deployment, resource, container, image)
    write_json(
        directory / "development-rollout.json",
        {
            "application": name,
            "revision": revision,
            "images": images,
            "release_sha256": hashlib.sha256(
                (directory / "release.json").read_bytes()
            ).hexdigest(),
        },
    )


def assemble(directory: Path, image_directory: Path, base: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    images = {
        name: load_image(
            json.loads((image_directory / f"{name}.json").read_text()), name
        )
        for name in REPOSITORIES
    }
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        release = verify_promotion(base, head())
        if release["images"] != images:
            raise ValueError(
                "Production image selection changed the promoted combination."
            )
        for name in (
            "release.json",
            "development-rollout.json",
            release["chart"]["filename"],
        ):
            shutil.copy2(base / name, directory / name)
        return
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("prepare", "select", "record", "assemble", "promote", "download"),
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--component", choices=tuple(REPOSITORIES))
    parser.add_argument("--digest", default="")
    parser.add_argument("--images", type=Path)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--revision", default="")
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()
    force = os.environ.get("REBUILD_IMAGES") == "true"
    if args.operation == "prepare":
        prepare(args.directory, force)
    elif args.operation == "assemble":
        if args.images is None or args.base is None:
            parser.error("Release assembly requires image records and a reuse base.")
        assemble(args.directory, args.images, args.base)
    elif args.operation == "download":
        if not download_release(args.directory, args.run_id, "launchpad-release"):
            raise ValueError("The selected App release artifact is unavailable.")
    elif args.operation == "promote":
        promote(args.directory, args.revision)
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
        image = select_image(component, args.directory, dependencies, force)
        if args.operation == "select":
            repository = REPOSITORIES[component]
            tag = os.environ["GITHUB_REF_NAME"]
            if component == "frontend":
                tag = head()
            elif os.environ["GITHUB_EVENT_NAME"] == "pull_request":
                tag = re.sub(r"[^a-z0-9_.-]", "-", os.environ["PR_BRANCH"].lower())
            elif os.environ["GITHUB_REF_TYPE"] != "tag":
                tag = "master"
            outputs(
                {
                    "build": str(image is None).lower(),
                    "image_ref": image["image_ref"] if image else "",
                    "tag": repository + ":" + tag,
                    "inputs_sha256": fingerprint(component, head(), dependencies),
                    "context": "frontend" if component == "frontend" else ".",
                    "dockerfile": {
                        "backend": "Dockerfile",
                        "frontend": "frontend/Dockerfile",
                        "hook": "hooks/hooks.Dockerfile",
                    }[component],
                }
            )
        else:
            if args.digest:
                image = {
                    "image_ref": REPOSITORIES[component]
                    + "@"
                    + text(args.digest, "sha256:" + SHA256),
                    "source_revision": head(),
                    "inputs_sha256": fingerprint(component, head(), dependencies),
                }
            if image is None:
                raise ValueError(
                    "A successful build or verified reusable image is required."
                )
            path = Path(f"{component}.json")
            write_json(path, image)
            outputs(
                {
                    "image_ref": image["image_ref"],
                    "image_digest": image["image_ref"].split("@", 1)[1],
                }
            )


if __name__ == "__main__":
    main()
