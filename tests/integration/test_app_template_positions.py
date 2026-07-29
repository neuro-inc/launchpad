from uuid import uuid4

from fastapi.testclient import TestClient


def _visible_templates(app_client: TestClient) -> list[dict[str, object]]:
    response = app_client.get("/api/v1/apps/templates?is_internal=false")
    assert response.status_code == 200
    return response.json()["items"]


def _import_template(app_client: TestClient, name: str) -> dict[str, object]:
    response = app_client.post(
        "/api/v1/apps/templates/import",
        json={"template_name": name, "template_version": "1.0.0"},
    )
    assert response.status_code == 200
    return response.json()


def test_template_positions_are_created_and_exposed(app_client: TestClient) -> None:
    initial_templates = _visible_templates(app_client)
    first = _import_template(app_client, "position-first")
    second = _import_template(app_client, "position-second")

    assert first["position"] == len(initial_templates)
    assert second["position"] == len(initial_templates) + 1

    internal_response = app_client.post(
        "/api/v1/apps/templates/import",
        json={
            "template_name": "position-internal",
            "template_version": "1.0.0",
            "is_internal": True,
        },
    )
    assert internal_response.status_code == 200
    assert internal_response.json()["position"] is None

    app_pool_response = app_client.get("/api/v1/apps")
    assert app_pool_response.status_code == 200
    app_pool = app_pool_response.json()["items"]
    assert [item["position"] for item in app_pool] == list(range(len(app_pool)))
    assert all("id" in item for item in app_pool)


def test_reorder_templates_updates_both_read_endpoints(app_client: TestClient) -> None:
    first = _import_template(app_client, "reorder-first")
    second = _import_template(app_client, "reorder-second")
    existing_ids = [template["id"] for template in _visible_templates(app_client)]
    requested_ids = [second["id"], first["id"]] + [
        template_id
        for template_id in existing_ids
        if template_id not in {first["id"], second["id"]}
    ]

    response = app_client.put(
        "/api/v1/apps/templates/order",
        json={"template_ids": requested_ids},
    )
    assert response.status_code == 204

    templates = _visible_templates(app_client)
    assert [template["id"] for template in templates] == requested_ids
    assert [template["position"] for template in templates] == list(
        range(len(requested_ids))
    )

    app_pool = app_client.get("/api/v1/apps").json()["items"]
    assert [app["id"] for app in app_pool] == requested_ids
    assert [app["position"] for app in app_pool] == list(range(len(requested_ids)))


def test_reorder_validation_uses_standard_fastapi_422(app_client: TestClient) -> None:
    template_ids = [template["id"] for template in _visible_templates(app_client)]

    duplicate_response = app_client.put(
        "/api/v1/apps/templates/order",
        json={"template_ids": [template_ids[0], template_ids[0]]},
    )
    assert duplicate_response.status_code == 422
    assert duplicate_response.json()["detail"][0]["loc"] == [
        "body",
        "template_ids",
    ]

    incomplete_response = app_client.put(
        "/api/v1/apps/templates/order",
        json={"template_ids": []},
    )
    assert incomplete_response.status_code == 422
    assert incomplete_response.json()["detail"][0]["loc"] == [
        "body",
        "template_ids",
    ]
    assert "refresh and retry" in incomplete_response.json()["detail"][0]["msg"]

    internal_templates = app_client.get(
        "/api/v1/apps/templates?is_internal=true"
    ).json()["items"]
    internal_response = app_client.put(
        "/api/v1/apps/templates/order",
        json={"template_ids": template_ids + [internal_templates[0]["id"]]},
    )
    assert internal_response.status_code == 422

    unknown_response = app_client.put(
        "/api/v1/apps/templates/order",
        json={"template_ids": template_ids + [str(uuid4())]},
    )
    assert unknown_response.status_code == 422

    malformed_response = app_client.put(
        "/api/v1/apps/templates/order",
        json={"template_ids": ["not-a-uuid"]},
    )
    assert malformed_response.status_code == 422


def test_delete_template_normalizes_remaining_positions(app_client: TestClient) -> None:
    first = _import_template(app_client, "delete-position-first")
    _import_template(app_client, "delete-position-second")

    response = app_client.delete(
        f"/api/v1/apps/templates/{first['id']}",
        params={"uninstall": False},
    )
    assert response.status_code == 204

    templates = _visible_templates(app_client)
    assert [template["position"] for template in templates] == list(
        range(len(templates))
    )


def test_visibility_changes_maintain_positions(app_client: TestClient) -> None:
    first = _import_template(app_client, "visibility-position-first")
    _import_template(app_client, "visibility-position-second")

    make_internal_response = app_client.post(
        "/api/v1/apps/templates/import",
        json={
            "template_name": "visibility-position-first",
            "template_version": "1.0.0",
            "is_internal": True,
        },
    )
    assert make_internal_response.status_code == 200
    assert make_internal_response.json()["id"] == first["id"]
    assert make_internal_response.json()["position"] is None
    visible_templates = _visible_templates(app_client)
    assert [template["position"] for template in visible_templates] == list(
        range(len(visible_templates))
    )

    make_visible_response = app_client.post(
        "/api/v1/apps/templates/import",
        json={
            "template_name": "visibility-position-first",
            "template_version": "1.0.0",
            "is_internal": False,
        },
    )
    assert make_visible_response.status_code == 200
    assert make_visible_response.json()["position"] == len(visible_templates)
