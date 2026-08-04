from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from launchpad.ext.app_configurator import (
    AUTH_INGRESS_MIDDLEWARE_TYPE,
    AppConfigurationPlan,
    AppConfigurator,
    discover_ingress_http_paths,
    patch_ingress_http_auth,
)


def test_discover_ingress_http_paths_resolves_refs_and_anyof() -> None:
    schema = {
        "properties": {
            "networking": {"$ref": "#/$defs/NetworkingConfig"},
        },
        "$defs": {
            "NetworkingConfig": {
                "type": "object",
                "properties": {
                    "ingress_http": {
                        "anyOf": [
                            {"$ref": "#/$defs/IngressHttp"},
                            {"type": "null"},
                        ],
                    },
                },
            },
            "IngressHttp": {
                "type": "object",
                "x-type": "IngressHttp",
                "properties": {"auth": {"type": "object"}},
            },
        },
    }

    assert discover_ingress_http_paths(schema) == [("networking", "ingress_http")]


def test_discover_ingress_http_paths_uses_x_type_only() -> None:
    schema = {
        "properties": {
            "networking": {"$ref": "#/$defs/NetworkingConfig"},
        },
        "$defs": {
            "NetworkingConfig": {
                "type": "object",
                "properties": {
                    "ingress_http": {
                        "title": "IngressHttp",
                        "type": "object",
                        "properties": {"auth": {"type": "object"}},
                    },
                },
            },
        },
    }

    assert discover_ingress_http_paths(schema) == []


def test_patch_ingress_http_auth_preserves_unrelated_input() -> None:
    current_input: dict[str, Any] = {
        "image": {"repository": "image://test"},
        "networking": {
            "ingress_http": {"port": 8080},
            "ports": [{"port": 8080}],
        },
    }
    original_input = deepcopy(current_input)

    updated_input, patched_paths, warnings = patch_ingress_http_auth(
        current_input=current_input,
        paths=[("networking", "ingress_http")],
        auth_middleware_name="platform-launchpad-auth-middleware",
    )

    assert current_input == original_input
    assert patched_paths == ["networking.ingress_http"]
    assert warnings == []
    assert updated_input["image"] == current_input["image"]
    assert updated_input["networking"]["ports"] == current_input["networking"]["ports"]
    assert updated_input["networking"]["ingress_http"]["auth"] == {
        "type": "custom_auth",
        "middleware": {
            "__type__": AUTH_INGRESS_MIDDLEWARE_TYPE,
            "name": "platform-launchpad-auth-middleware",
        },
    }


def test_patch_ingress_http_auth_replaces_existing_auth_only() -> None:
    current_input = {
        "networking": {
            "ingress_http": {
                "path": "/",
                "auth": {
                    "type": "custom_auth",
                    "middleware": {
                        "__type__": AUTH_INGRESS_MIDDLEWARE_TYPE,
                        "name": "old-middleware",
                    },
                },
            },
        },
    }

    updated_input, patched_paths, warnings = patch_ingress_http_auth(
        current_input=current_input,
        paths=[("networking", "ingress_http")],
        auth_middleware_name="new-middleware",
    )

    assert patched_paths == ["networking.ingress_http"]
    assert warnings == []
    assert updated_input["networking"]["ingress_http"]["path"] == "/"
    assert (
        updated_input["networking"]["ingress_http"]["auth"]["middleware"]["name"]
        == "new-middleware"
    )


def test_patch_ingress_http_auth_warns_for_missing_path() -> None:
    updated_input, patched_paths, warnings = patch_ingress_http_auth(
        current_input={"networking": {}},
        paths=[("networking", "ingress_http")],
        auth_middleware_name="middleware",
    )

    assert updated_input == {"networking": {}}
    assert patched_paths == []
    assert warnings == [
        "Cannot configure auth middleware at networking.ingress_http: input value is missing or null"
    ]


@pytest.mark.asyncio
async def test_app_configurator_calls_configure_when_input_changes() -> None:
    app_id = uuid4()
    previous_launchpad_id = uuid4()
    apps_api_client = SimpleNamespace()
    apps_api_client.get_by_id = AsyncMock(
        return_value={
            "template_name": "service-deployment",
            "template_version": "v1",
        }
    )
    apps_api_client.get_inputs = AsyncMock(
        return_value={
            "networking": {
                "ingress_http": {
                    "path": "/",
                    "auth": {
                        "type": "custom_auth",
                        "middleware": {
                            "__type__": AUTH_INGRESS_MIDDLEWARE_TYPE,
                            "name": f"platform-launchpad-{previous_launchpad_id.hex}-auth-middleware",
                        },
                    },
                },
            },
        }
    )
    apps_api_client.get_template = AsyncMock(
        return_value={
            "input": {
                "properties": {"networking": {"$ref": "#/$defs/NetworkingConfig"}},
                "$defs": {
                    "NetworkingConfig": {
                        "type": "object",
                        "properties": {"ingress_http": {"$ref": "#/$defs/IngressHttp"}},
                    },
                    "IngressHttp": {
                        "type": "object",
                        "x-type": "IngressHttp",
                        "properties": {"auth": {"type": "object"}},
                    },
                },
            }
        }
    )
    apps_api_client.configure_app = AsyncMock()

    configurator = AppConfigurator(
        apps_api_client=cast(Any, apps_api_client),
        auth_middleware_name="launchpad-middleware",
        launchpad_instance_id=uuid4(),
    )

    plan = await configurator.prepare_launchpad_auth(app_id)
    apps_api_client.configure_app.assert_not_awaited()
    result = await configurator.apply_launchpad_auth(plan)

    assert result.changed is True
    assert result.warnings == []
    assert result.previous_launchpad_instance_ids == [previous_launchpad_id]
    apps_api_client.configure_app.assert_awaited_once()
    assert apps_api_client.configure_app.await_args.args[0] == app_id
    configure_kwargs = apps_api_client.configure_app.await_args.kwargs
    assert (
        configure_kwargs["inputs"]["networking"]["ingress_http"]["auth"]["middleware"][
            "name"
        ]
        == "launchpad-middleware"
    )


@pytest.mark.asyncio
async def test_app_configurator_skips_configure_when_input_is_unchanged() -> None:
    app_id = uuid4()
    configured_input = {
        "networking": {
            "ingress_http": {
                "auth": {
                    "type": "custom_auth",
                    "middleware": {
                        "__type__": AUTH_INGRESS_MIDDLEWARE_TYPE,
                        "name": "launchpad-middleware",
                    },
                },
            },
        },
    }
    apps_api_client = SimpleNamespace()
    apps_api_client.get_by_id = AsyncMock(
        return_value={
            "template_name": "service-deployment",
            "template_version": "v1",
        }
    )
    apps_api_client.get_inputs = AsyncMock(return_value=configured_input)
    apps_api_client.get_template = AsyncMock(
        return_value={
            "input": {
                "properties": {"networking": {"$ref": "#/$defs/NetworkingConfig"}},
                "$defs": {
                    "NetworkingConfig": {
                        "type": "object",
                        "properties": {"ingress_http": {"$ref": "#/$defs/IngressHttp"}},
                    },
                    "IngressHttp": {
                        "type": "object",
                        "x-type": "IngressHttp",
                        "properties": {"auth": {"type": "object"}},
                    },
                },
            }
        }
    )
    apps_api_client.configure_app = AsyncMock()

    configurator = AppConfigurator(
        apps_api_client=cast(Any, apps_api_client),
        auth_middleware_name="launchpad-middleware",
        launchpad_instance_id=uuid4(),
    )

    plan = await configurator.prepare_launchpad_auth(app_id)
    result = await configurator.apply_launchpad_auth(plan)

    assert result.changed is False
    assert result.warnings == []
    apps_api_client.configure_app.assert_not_awaited()


@pytest.mark.parametrize(
    ("failure_stage", "warning_fragment"),
    [
        ("app", "failed to fetch app metadata"),
        ("input", "failed to fetch current app input"),
        ("template", "failed to fetch template schema"),
        ("schema", "template schema is unavailable"),
        ("paths", "no IngressHttp input found"),
        ("patch", "no patchable IngressHttp input found"),
    ],
)
async def test_prepare_launchpad_auth_failure_paths(
    failure_stage: str,
    warning_fragment: str,
) -> None:
    apps_api_client = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value={"template_name": "template", "template_version": "v1"}
        ),
        get_inputs=AsyncMock(return_value={}),
        get_template=AsyncMock(return_value={"input": {}}),
        configure_app=AsyncMock(),
    )
    if failure_stage == "app":
        apps_api_client.get_by_id.side_effect = RuntimeError("failure")
    elif failure_stage == "input":
        apps_api_client.get_inputs.side_effect = RuntimeError("failure")
    elif failure_stage == "template":
        apps_api_client.get_template.side_effect = RuntimeError("failure")
    elif failure_stage == "schema":
        apps_api_client.get_template.return_value = {}
    elif failure_stage == "patch":
        apps_api_client.get_template.return_value = {
            "input": {
                "properties": {"ingress": {"type": "object", "x-type": "IngressHttp"}}
            }
        }

    configurator = AppConfigurator(
        apps_api_client=cast(Any, apps_api_client),
        auth_middleware_name="middleware",
        launchpad_instance_id=uuid4(),
    )

    plan = await configurator.prepare_launchpad_auth(uuid4())

    assert warning_fragment in plan.warnings[0]
    apps_api_client.configure_app.assert_not_awaited()


async def test_apply_launchpad_auth_uses_unknown_instance_fallback() -> None:
    apps_api_client = SimpleNamespace(configure_app=AsyncMock())
    configurator = AppConfigurator(
        apps_api_client=cast(Any, apps_api_client),
        auth_middleware_name="middleware",
        launchpad_instance_id=None,
    )
    plan = AppConfigurationPlan(
        app_id=uuid4(),
        template_name="template",
        template_version="v1",
        updated_input={"ingress": {}},
    )

    result = await configurator.apply_launchpad_auth(plan)

    assert result.changed is True
    assert "instance id is not configured" in result.warnings[0]
    assert (
        "Launchpad unknown"
        in apps_api_client.configure_app.await_args.kwargs["comment"]
    )
