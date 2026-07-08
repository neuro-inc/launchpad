from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from launchpad.ext.app_configurator import (
    AUTH_INGRESS_MIDDLEWARE_TYPE,
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

    result = await configurator.configure_launchpad_auth(app_id)

    assert result.changed is True
    assert result.warnings == []
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

    result = await configurator.configure_launchpad_auth(app_id)

    assert result.changed is False
    assert result.warnings == []
    apps_api_client.configure_app.assert_not_awaited()
