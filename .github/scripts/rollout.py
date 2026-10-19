"""Verify the runtime images and chart source of a synchronized App."""

from typing import TypedDict


class Rollout(TypedDict):
    health: str
    sync: str
    phase: str
    chart_index: int
    revisions: tuple[str, ...]
    completed_revisions: tuple[str, ...]


def _object_field(parent: object, name: str) -> dict[str, object]:
    value: object = parent.get(name) if isinstance(parent, dict) else None
    if not isinstance(value, dict):
        raise ValueError(f"The Argo CD response must contain an object for {name}.")
    return value


def _text_field(parent: dict[str, object], name: str) -> str:
    value = parent.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"The Argo CD response must contain nonempty text for {name}.")
    return value


def _revisions(parent: dict[str, object], source_count: int) -> tuple[str, ...]:
    values = parent.get("revisions")
    if values is None and source_count == 1:
        return (_text_field(parent, "revision"),)
    if not isinstance(values, list) or len(values) != source_count:
        raise ValueError(
            "The Argo CD revisions must identify every application source."
        )
    if not all(isinstance(value, str) and value for value in values):
        raise ValueError("The Argo CD revisions must contain nonempty text.")
    return tuple(values)


def parse_rollout(application: object) -> Rollout:
    spec = _object_field(application, "spec")
    sources = spec.get("sources")
    if sources is None:
        sources = [_object_field(spec, "source")]
    if not isinstance(sources, list) or not sources:
        raise ValueError("The Argo CD application must identify its chart sources.")
    chart_indices = []
    for index, value in enumerate(sources):
        source = _object_field({"source": value}, "source")
        if (
            source.get("repoURL")
            in {
                "https://github.com/neuro-inc/launchpad",
                "https://github.com/neuro-inc/launchpad.git",
            }
            and source.get("path") == "charts/launchpad"
        ):
            chart_indices.append(index)
    if len(chart_indices) != 1:
        raise ValueError(
            "The Argo CD application must identify one Launchpad chart source."
        )
    status = _object_field(application, "status")
    sync = _object_field(status, "sync")
    operation = _object_field(status, "operationState")
    return {
        "health": _text_field(_object_field(status, "health"), "status"),
        "sync": _text_field(sync, "status"),
        "phase": _text_field(operation, "phase"),
        "chart_index": chart_indices[0],
        "revisions": _revisions(sync, len(sources)),
        "completed_revisions": _revisions(
            _object_field(operation, "syncResult"), len(sources)
        ),
    }


def verify_rollout(application: object) -> str:
    rollout = parse_rollout(application)
    is_current_sync = (
        rollout["sync"] == "Synced"
        and rollout["completed_revisions"] == rollout["revisions"]
    )
    is_healthy_completion = (
        rollout["health"] == "Healthy" and rollout["phase"] == "Succeeded"
    )
    if not (is_current_sync and is_healthy_completion):
        raise ValueError(
            "Development must confirm the exact healthy Argo CD revisions."
        )
    return rollout["revisions"][rollout["chart_index"]]


class DeploymentResource(TypedDict):
    name: str
    namespace: str
    app_namespace: str


def runtime_resources(
    application: object,
) -> tuple[DeploymentResource, DeploymentResource]:
    app_namespace = _text_field(_object_field(application, "metadata"), "namespace")
    resources = _object_field(application, "status").get("resources")
    if not isinstance(resources, list):
        raise ValueError("The Argo CD application must identify its managed resources.")
    deployments: list[DeploymentResource] = []
    for value in resources:
        resource = _object_field({"resource": value}, "resource")
        if resource.get("group") == "apps" and resource.get("kind") == "Deployment":
            deployments.append(
                {
                    "name": _text_field(resource, "name"),
                    "namespace": _text_field(resource, "namespace"),
                    "app_namespace": app_namespace,
                }
            )
    by_identity = {(item["namespace"], item["name"]): item for item in deployments}
    if len(by_identity) != len(deployments):
        raise ValueError("The App contains duplicate Deployment identities.")
    pairs = []
    for backend in deployments:
        frontend = by_identity.get((backend["namespace"], backend["name"] + "-client"))
        if backend["name"].startswith("launchpad-") and frontend is not None:
            pairs.append((backend, frontend))
    if len(pairs) != 1:
        raise ValueError(
            "The App must identify one backend and frontend Deployment pair."
        )
    return pairs[0]


def verify_deployment(
    deployment: object, resource: DeploymentResource, container_name: str, image: str
) -> None:
    value = _object_field({"deployment": deployment}, "deployment")
    metadata = _object_field(value, "metadata")
    is_managed_deployment = (
        value.get("apiVersion") == "apps/v1"
        and value.get("kind") == "Deployment"
        and metadata.get("name") == resource["name"]
        and metadata.get("namespace") == resource["namespace"]
        and not metadata.get("deletionTimestamp")
    )
    if not is_managed_deployment:
        raise ValueError("The live Deployment does not match the managed resource.")
    spec = _object_field(value, "spec")
    status = _object_field(value, "status")
    generation = metadata.get("generation")
    replicas = spec.get("replicas", 1)
    if type(generation) is not int or type(replicas) is not int:
        raise ValueError(
            "The Deployment generation and replica count must be integers."
        )
    is_current_generation = (
        generation > 0
        and type(status.get("observedGeneration")) is int
        and status.get("observedGeneration") == generation
    )
    unavailable = status.get("unavailableReplicas", 0)
    is_complete_rollout = (
        replicas > 0
        and type(unavailable) is int
        and unavailable == 0
        and all(
            type(status.get(key)) is int and status.get(key) == replicas
            for key in (
                "replicas",
                "updatedReplicas",
                "readyReplicas",
                "availableReplicas",
            )
        )
    )
    is_ready = is_current_generation and is_complete_rollout and not spec.get("paused")
    if not is_ready:
        raise ValueError("The selected Deployment rollout is not complete.")
    containers = _object_field(_object_field(spec, "template"), "spec").get(
        "containers"
    )
    if not isinstance(containers, list):
        raise ValueError("The Deployment must identify its runtime containers.")
    selected = []
    for item in containers:
        container = _object_field({"container": item}, "container")
        if container.get("name") == container_name:
            selected.append(container)
    if len(selected) != 1 or selected[0].get("image") != image:
        raise ValueError("The live Deployment does not run the selected runtime image.")
