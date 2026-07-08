import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from launchpad.ext.apps_api import AppsApiClient


logger = logging.getLogger(__name__)


Path = tuple[str, ...]
AUTH_INGRESS_MIDDLEWARE_TYPE = "AuthIngressMiddleware"


@dataclass(frozen=True)
class AppConfigurationResult:
    changed: bool = False
    warnings: list[str] = field(default_factory=list)


def _format_path(path: Path) -> str:
    return ".".join(path) if path else "<root>"


def _decode_json_pointer_part(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any] | None:
    if not ref.startswith("#/"):
        return None

    current: Any = schema
    for raw_part in ref[2:].split("/"):
        part = _decode_json_pointer_part(raw_part)
        if not isinstance(current, dict):
            return None
        current = current.get(part)

    return current if isinstance(current, dict) else None


def _resolve_schema_node(
    root_schema: dict[str, Any],
    node: dict[str, Any],
) -> dict[str, Any]:
    seen_refs: set[str] = set()
    current = node

    while "$ref" in current:
        ref = current["$ref"]
        if not isinstance(ref, str) or ref in seen_refs:
            return current
        seen_refs.add(ref)

        resolved = _resolve_ref(root_schema, ref)
        if resolved is None:
            return current

        current = resolved

    return current


def _is_ingress_http_schema(root_schema: dict[str, Any], node: dict[str, Any]) -> bool:
    resolved = _resolve_schema_node(root_schema, node)
    return resolved.get("x-type") == "IngressHttp"


def discover_ingress_http_paths(schema: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    seen_nodes: set[tuple[int, Path]] = set()

    def walk(node: dict[str, Any], path: Path) -> None:
        resolved = _resolve_schema_node(schema, node)
        seen_key = (id(resolved), path)
        if seen_key in seen_nodes:
            return
        seen_nodes.add(seen_key)

        if resolved.get("x-type") == "IngressHttp":
            paths.append(path)
            return

        for branch_key in ("anyOf", "oneOf", "allOf"):
            branches = resolved.get(branch_key)
            if isinstance(branches, list):
                for branch in branches:
                    if isinstance(branch, dict):
                        walk(branch, path)

        properties = resolved.get("properties")
        if not isinstance(properties, dict):
            return

        for property_name, property_schema in properties.items():
            if not isinstance(property_name, str) or not isinstance(
                property_schema, dict
            ):
                continue

            next_path = (*path, property_name)
            if _is_ingress_http_schema(schema, property_schema):
                paths.append(next_path)
                continue

            walk(property_schema, next_path)

    walk(schema, ())

    deduplicated_paths: list[Path] = []
    seen_paths: set[Path] = set()
    for path in paths:
        if path not in seen_paths:
            deduplicated_paths.append(path)
            seen_paths.add(path)

    return deduplicated_paths


def _get_path_value(data: dict[str, Any], path: Path) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def patch_ingress_http_auth(
    current_input: dict[str, Any],
    paths: list[Path],
    auth_middleware_name: str,
) -> tuple[dict[str, Any], list[str], list[str]]:
    updated_input = deepcopy(current_input)
    patched_paths: list[str] = []
    warnings: list[str] = []
    auth_config = {
        "auth": {
            "type": "custom_auth",
            "middleware": {
                "__type__": AUTH_INGRESS_MIDDLEWARE_TYPE,
                "name": auth_middleware_name,
            },
        }
    }

    for path in paths:
        target = _get_path_value(updated_input, path)
        formatted_path = _format_path(path)

        if target is None:
            warnings.append(
                f"Cannot configure auth middleware at {formatted_path}: input value is missing or null"
            )
            continue

        if not isinstance(target, dict):
            warnings.append(
                f"Cannot configure auth middleware at {formatted_path}: input value is not an object"
            )
            continue

        target.update(deepcopy(auth_config))
        patched_paths.append(formatted_path)

    return updated_input, patched_paths, warnings


class AppConfigurator:
    def __init__(
        self,
        apps_api_client: AppsApiClient,
        auth_middleware_name: str,
        launchpad_instance_id: UUID | None,
    ):
        self._apps_api_client = apps_api_client
        self._auth_middleware_name = auth_middleware_name
        self._launchpad_instance_id = launchpad_instance_id

    async def configure_launchpad_auth(
        self,
        app_id: UUID,
    ) -> AppConfigurationResult:
        warnings: list[str] = []

        try:
            app = await self._apps_api_client.get_by_id(app_id)
        except Exception as e:
            logger.warning("Failed to fetch app %s from Apps API: %s", app_id, e)
            return AppConfigurationResult(
                warnings=[
                    f"Auth middleware was not configured: failed to fetch app metadata for {app_id}"
                ]
            )

        template_name = app["template_name"]
        template_version = app["template_version"]

        try:
            current_input = await self._apps_api_client.get_inputs(app_id)
        except Exception as e:
            logger.warning("Failed to fetch app %s input from Apps API: %s", app_id, e)
            return AppConfigurationResult(
                warnings=[
                    f"Auth middleware was not configured for {template_name}:{template_version}: failed to fetch current app input"
                ]
            )

        try:
            template = await self._apps_api_client.get_template(
                template_name, template_version
            )
        except Exception as e:
            logger.warning(
                "Failed to fetch template schema for %s:%s from Apps API: %s",
                template_name,
                template_version,
                e,
            )
            return AppConfigurationResult(
                warnings=[
                    f"Auth middleware was not configured for {template_name}:{template_version}: failed to fetch template schema"
                ]
            )

        schema = template.get("input")
        if not isinstance(schema, dict):
            return AppConfigurationResult(
                warnings=[
                    f"Auth middleware was not configured for {template_name}:{template_version}: template schema is unavailable"
                ]
            )

        paths = discover_ingress_http_paths(schema)
        if not paths:
            return AppConfigurationResult(
                warnings=[
                    f"Auth middleware was not configured for {template_name}:{template_version}: no IngressHttp input found in template schema"
                ]
            )

        updated_input, patched_paths, patch_warnings = patch_ingress_http_auth(
            current_input=current_input,
            paths=paths,
            auth_middleware_name=self._auth_middleware_name,
        )
        warnings.extend(patch_warnings)

        if not patched_paths:
            return AppConfigurationResult(
                warnings=[
                    f"Auth middleware was not configured for {template_name}:{template_version}: no patchable IngressHttp input found",
                    *warnings,
                ]
            )

        if updated_input == current_input:
            logger.info(
                "App %s already has Launchpad auth middleware configured at %s",
                app_id,
                patched_paths,
            )
            return AppConfigurationResult(warnings=warnings)

        if self._launchpad_instance_id is None:
            warnings.append(
                "Launchpad instance id is not configured; using local import comment fallback"
            )
            instance = "unknown"
        else:
            instance = str(self._launchpad_instance_id)

        comment = f"Import into Launchpad {instance}: change auth middleware"
        try:
            await self._apps_api_client.configure_app(
                app_id,
                inputs=updated_input,
                comment=comment,
            )
        except Exception as e:
            logger.warning(
                "Failed to configure Launchpad auth middleware for app %s: %s",
                app_id,
                e,
            )
            return AppConfigurationResult(
                warnings=[
                    f"Auth middleware was not configured for {template_name}:{template_version}: app reconfiguration failed",
                    *warnings,
                ]
            )

        logger.info(
            "Configured Launchpad auth middleware for app %s at input paths: %s",
            app_id,
            patched_paths,
        )
        return AppConfigurationResult(changed=True, warnings=warnings)
