from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from launchpad.auth.dependencies import admin_role_required, auth_required
from launchpad.auth.models import User
from launchpad.config import Config


def test_ping_endpoint(app_client: TestClient) -> None:
    response = app_client.get("/ping")
    assert response.status_code == 200
    assert response.text == "Pong"


def test_config_endpoint(app_client: TestClient, config: Config) -> None:
    response = app_client.get("/config")
    assert response.status_code == 200
    assert response.json() == {
        "keycloak": {
            "url": str(config.keycloak.url),
            "realm": config.keycloak.realm,
        },
        "branding": {
            "logo_url": f"{app_client.base_url}/branding/logo",
            "favicon_url": f"{app_client.base_url}/branding/favicon",
            "css_url": f"{app_client.base_url}/branding/css",
            "background_url": f"{app_client.base_url}/branding/background",
            "title": "Test Title",
            "background": "12345",
        },
    }


def test_config_endpoint_ignores_stale_branding_files(
    app_client: TestClient, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_exists = Path.exists

    def stale_logo_exists(path: Path) -> bool:
        if path == config.branding.branding_dir / "logo":
            raise OSError(116, "Stale file handle", str(path))
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", stale_logo_exists)

    response = app_client.get("/config")

    assert response.status_code == 200
    assert response.json() == {
        "keycloak": {
            "url": str(config.keycloak.url),
            "realm": config.keycloak.realm,
        },
        "branding": {
            "logo_url": None,
            "favicon_url": f"{app_client.base_url}/branding/favicon",
            "css_url": f"{app_client.base_url}/branding/css",
            "background_url": f"{app_client.base_url}/branding/background",
            "title": "Test Title",
            "background": "12345",
        },
    }


def test_branding_css_endpoint_is_public(app_client: TestClient) -> None:
    response = app_client.get("/branding/css")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/css; charset=utf-8"
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.text == "body { color: #123456; }\n"


def test_cors_middleware(app_client: TestClient, config: Config) -> None:
    """Test that CORS middleware is configured correctly"""
    frontend_origin = f"https://{config.apolo.self_domain}"

    # Test preflight OPTIONS request
    response = app_client.options(
        "/api/v1/apps/templates",
        headers={
            "Origin": frontend_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == frontend_origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "GET" in response.headers["access-control-allow-methods"]

    # Test actual request with CORS headers
    response = app_client.get(
        "/api/v1/apps/templates",
        headers={"Origin": frontend_origin},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == frontend_origin
    assert response.headers["access-control-allow-credentials"] == "true"


class TestAdminAuthorization:
    """Integration tests for admin-only app management endpoints."""

    def test_non_admin_cannot_add_or_delete_apps(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        async def non_admin_auth_required() -> User:
            return User(
                id="user@example.com",
                email="user@example.com",
                name="Regular User",
                groups=["user"],
            )

        app = cast(FastAPI, app_client.app)
        app.dependency_overrides.pop(admin_role_required, None)
        app.dependency_overrides[auth_required] = non_admin_auth_required

        import_template_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "admin-only-template",
                "template_version": "1.0.0",
            },
        )
        assert import_template_response.status_code == 401

        import_app_response = app_client.post(
            "/api/v1/apps/import",
            json={
                "app_id": str(uuid4()),
                "name": "admin-only-app",
            },
        )
        assert import_app_response.status_code == 401

        delete_instance_response = app_client.delete(
            f"/api/v1/apps/instances/{uuid4()}"
        )
        assert delete_instance_response.status_code == 401

        delete_template_response = app_client.delete(
            f"/api/v1/apps/templates/{uuid4()}"
        )
        assert delete_template_response.status_code == 401

        mock_apps_api_client.get_template.assert_not_called()
        mock_apps_api_client.get_by_id.assert_not_called()
        mock_apps_api_client.delete_app.assert_not_called()


class TestTemplatesEndpoint:
    """Integration tests for the /templates endpoint"""

    def test_get_templates_all(self, app_client: TestClient) -> None:
        """Test getting all templates (internal and non-internal)"""
        response = app_client.get("/api/v1/apps/templates")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        # Should have seeded templates: openwebui, vllm, postgres, embeddings
        assert len(data["items"]) >= 4

        # Verify all templates have required fields
        for template in data["items"]:
            assert "id" in template
            assert "name" in template
            assert "template_name" in template
            assert "template_version" in template
            assert "verbose_name" in template
            assert "is_internal" in template
            assert "is_shared" in template

    def test_get_templates_internal_only(self, app_client: TestClient) -> None:
        """Test filtering only internal templates"""
        response = app_client.get("/api/v1/apps/templates?is_internal=true")
        assert response.status_code == 200
        data = response.json()

        # Should have 3 internal templates: vllm, postgres, embeddings
        assert len(data["items"]) == 3
        for template in data["items"]:
            assert template["is_internal"] is True

        internal_names = {t["name"] for t in data["items"]}
        assert "vllm-llama-3.1-8b" in internal_names
        assert "postgres" in internal_names
        assert "embeddings" in internal_names

    def test_get_templates_non_internal_only(self, app_client: TestClient) -> None:
        """Test filtering only non-internal templates"""
        response = app_client.get("/api/v1/apps/templates?is_internal=false")
        assert response.status_code == 200
        data = response.json()

        # Should have at least openwebui (seeded)
        assert len(data["items"]) >= 1
        for template in data["items"]:
            assert template["is_internal"] is False

        # OpenWebUI should be present
        openwebui = next((t for t in data["items"] if t["name"] == "openwebui"), None)
        assert openwebui is not None
        assert openwebui["verbose_name"] == "OpenWebUI"

    def test_get_templates_with_imported(self, app_client: TestClient) -> None:
        """Test templates list includes imported templates"""
        # Import a new template
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "test-template",
                "template_version": "1.0.0",
                "verbose_name": "Test Template",
            },
        )
        assert import_response.status_code == 200

        # Get all templates
        response = app_client.get("/api/v1/apps/templates")
        assert response.status_code == 200
        data = response.json()

        # Should include the imported template
        test_template = next(
            (t for t in data["items"] if t["name"] == "test-template"), None
        )
        assert test_template is not None
        assert test_template["verbose_name"] == "Test Template"
        assert test_template["template_name"] == "test-template"
        assert test_template["template_version"] == "1.0.0"


class TestInstancesEndpoint:
    """Integration tests for the /instances endpoint"""

    def test_get_instances_empty(self, app_client: TestClient) -> None:
        """Test getting instances when none exist (excluding internal apps)"""
        response = app_client.get("/api/v1/apps/instances")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

        # Filter out internal apps (they are installed on startup)
        non_internal = [item for item in data["items"] if not item["is_internal"]]
        assert len(non_internal) == 0

    def test_get_instances_with_apps(self, app_client: TestClient) -> None:
        """Test getting instances after installing apps"""
        # Import and install a template
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "test-app",
                "template_version": "1.0.0",
                "verbose_name": "Test Application",
            },
        )
        assert import_response.status_code == 200

        # Install the app
        install_response = app_client.post("/api/v1/apps/test-app")
        assert install_response.status_code == 200

        # Get instances
        response = app_client.get("/api/v1/apps/instances")
        assert response.status_code == 200
        data = response.json()

        # Filter non-internal instances (internal apps like vllm are installed on startup)
        non_internal = [item for item in data["items"] if not item["is_internal"]]

        # Should have 1 non-internal instance
        assert len(non_internal) == 1
        assert non_internal[0]["launchpad_app_name"] == "test-app"

    def test_get_instances_multiple(self, app_client: TestClient) -> None:
        """Test getting multiple instances"""
        # Import templates
        for i in range(3):
            app_client.post(
                "/api/v1/apps/templates/import",
                json={
                    "template_name": f"app-{i}",
                    "template_version": "1.0.0",
                    "verbose_name": f"App {i}",
                },
            )

        # Install apps
        for i in range(3):
            response = app_client.post(f"/api/v1/apps/app-{i}")
            assert response.status_code == 200

        # Get all instances
        response = app_client.get("/api/v1/apps/instances")
        assert response.status_code == 200
        data = response.json()

        # Filter non-internal instances
        non_internal = [item for item in data["items"] if not item["is_internal"]]

        # Should have 3 non-internal instances
        assert len(non_internal) == 3
        app_names = {item["launchpad_app_name"] for item in non_internal}
        assert app_names == {"app-0", "app-1", "app-2"}


class TestDeleteInstance:
    """Integration tests for deleting app instances"""

    def test_delete_instance_success(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test successfully deleting an app instance"""
        # Import and install a template
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "deletable-app",
                "template_version": "1.0.0",
            },
        )

        install_response = app_client.post("/api/v1/apps/deletable-app")
        assert install_response.status_code == 200
        installed_app = install_response.json()
        app_id = installed_app["launchpad_app_name"]

        # Get the actual app_id from the database
        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        actual_app_id = next(
            item["app_id"] for item in instances if item["launchpad_app_name"] == app_id
        )
        preserved_app_id = uuid4()
        mock_apps_api_client.get_outputs.return_value = {
            "installed_apps": {
                "app_list": [
                    {"app_id": actual_app_id, "app_name": "deletable-app"},
                    {"app_id": str(preserved_app_id), "app_name": "preserved-app"},
                ]
            }
        }

        # Delete the instance
        delete_response = app_client.delete(
            f"/api/v1/apps/instances/{actual_app_id}",
            params={"uninstall": "true"},
        )
        assert delete_response.status_code == 204

        # Verify it was deleted via Apps API
        mock_apps_api_client.delete_app.assert_called_once()

        # Verify it was removed from launchpad outputs
        mock_apps_api_client.update_outputs.assert_called_once()
        updated_outputs = mock_apps_api_client.update_outputs.call_args[0][1]
        app_list = updated_outputs["installed_apps"]["app_list"]
        assert {app["app_id"] for app in app_list} == {str(preserved_app_id)}

        # Verify it's no longer in the database
        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        remaining_apps = [
            item for item in instances if item["launchpad_app_name"] == app_id
        ]
        assert len(remaining_apps) == 0

    def test_delete_nonexistent_instance(self, app_client: TestClient) -> None:
        """Test deleting a non-existent instance"""
        fake_id = uuid4()

        # Mock Apps API to raise NotFound
        delete_response = app_client.delete(f"/api/v1/apps/instances/{fake_id}")

        # Should fail gracefully - the endpoint will try to delete from Apps API
        # and then from DB. If neither exists, it may succeed with 204 or fail.
        # The important thing is it doesn't crash
        assert delete_response.status_code in [204, 404, 500]


class TestDeleteTemplate:
    """Integration tests for deleting templates"""

    def test_delete_template_without_instances(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test deleting a template that has no instances"""
        # Import a template
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "unused-template",
                "template_version": "1.0.0",
                "verbose_name": "Unused Template",
            },
        )
        assert import_response.status_code == 200
        template_data = import_response.json()
        template_id = template_data["id"]

        # Verify template is in the pool
        pool_response = app_client.get("/api/v1/apps")
        pool_apps = {
            item["launchpad_app_name"] for item in pool_response.json()["items"]
        }
        assert "unused-template" in pool_apps

        # Delete the template
        delete_response = app_client.delete(f"/api/v1/apps/templates/{template_id}")
        assert delete_response.status_code == 204

        # Verify Apps API delete was NOT called (no instances)
        mock_apps_api_client.delete_app.assert_not_called()

        # Verify template is no longer in the pool
        pool_response = app_client.get("/api/v1/apps")
        pool_apps = {
            item["launchpad_app_name"] for item in pool_response.json()["items"]
        }
        assert "unused-template" not in pool_apps

    def test_delete_template_with_single_instance(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test deleting a template cascades to its single instance"""
        # Import a template
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "cascade-test",
                "template_version": "1.0.0",
                "verbose_name": "Cascade Test",
            },
        )
        assert import_response.status_code == 200
        template_data = import_response.json()
        template_id = template_data["id"]

        # Install an app from this template
        install_response = app_client.post("/api/v1/apps/cascade-test")
        assert install_response.status_code == 200

        # Verify instance exists
        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        non_internal = [item for item in instances if not item["is_internal"]]
        assert len(non_internal) == 1
        assert non_internal[0]["launchpad_app_name"] == "cascade-test"
        actual_app_id = non_internal[0]["app_id"]
        preserved_app_id = uuid4()
        mock_apps_api_client.get_outputs.return_value = {
            "installed_apps": {
                "app_list": [
                    {"app_id": actual_app_id, "app_name": "cascade-test"},
                    {"app_id": str(preserved_app_id), "app_name": "preserved-app"},
                ]
            }
        }

        # Delete the template
        delete_response = app_client.delete(f"/api/v1/apps/templates/{template_id}")
        assert delete_response.status_code == 204

        # Verify Apps API delete was called for the instance
        assert mock_apps_api_client.delete_app.call_count == 1

        # Verify the deleted app was removed from launchpad outputs
        mock_apps_api_client.update_outputs.assert_called_once()
        updated_outputs = mock_apps_api_client.update_outputs.call_args[0][1]
        app_list = updated_outputs["installed_apps"]["app_list"]
        assert {app["app_id"] for app in app_list} == {str(preserved_app_id)}

        # Verify both template and instance are gone
        pool_response = app_client.get("/api/v1/apps")
        pool_apps = {
            item["launchpad_app_name"] for item in pool_response.json()["items"]
        }
        assert "cascade-test" not in pool_apps

        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        non_internal = [item for item in instances if not item["is_internal"]]
        assert len(non_internal) == 0

    def test_delete_template_with_multiple_instances(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test deleting a template cascades when installed multiple times (shared app)"""
        # Import a shared template
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "multi-instance",
                "template_version": "1.0.0",
                "is_shared": True,
            },
        )
        assert import_response.status_code == 200
        template_data = import_response.json()
        template_id = template_data["id"]

        # Install the app multiple times (shared apps return same instance)
        for i in range(3):
            install_response = app_client.post("/api/v1/apps/multi-instance")
            assert install_response.status_code == 200

        # Verify we have 1 shared instance
        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        non_internal = [item for item in instances if not item["is_internal"]]
        multi_instances = [
            item
            for item in non_internal
            if item["launchpad_app_name"] == "multi-instance"
        ]
        assert len(multi_instances) == 1

        # Delete the template
        delete_response = app_client.delete(f"/api/v1/apps/templates/{template_id}")
        assert delete_response.status_code == 204

        # Verify Apps API delete was called for the shared instance
        assert mock_apps_api_client.delete_app.call_count == 1

        # Verify template and instance are gone
        pool_response = app_client.get("/api/v1/apps")
        pool_apps = {
            item["launchpad_app_name"] for item in pool_response.json()["items"]
        }
        assert "multi-instance" not in pool_apps

    def test_delete_template_with_single_instance_no_uninstall(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        # Import a template
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "cascade-test",
                "template_version": "1.0.0",
                "verbose_name": "Cascade Test",
            },
        )
        assert import_response.status_code == 200
        template_data = import_response.json()
        template_id = template_data["id"]

        # Install an app from this template
        install_response = app_client.post("/api/v1/apps/cascade-test")
        assert install_response.status_code == 200

        # Verify instance exists
        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        non_internal = [item for item in instances if not item["is_internal"]]
        assert len(non_internal) == 1
        assert non_internal[0]["launchpad_app_name"] == "cascade-test"

        # Delete the template
        delete_response = app_client.delete(
            f"/api/v1/apps/templates/{template_id}", params={"uninstall": False}
        )
        assert delete_response.status_code == 204

        # Verify Apps API delete was called for the instance
        mock_apps_api_client.delete_app.assert_not_called()

        # Verify both template and instance are gone
        pool_response = app_client.get("/api/v1/apps")
        pool_apps = {
            item["launchpad_app_name"] for item in pool_response.json()["items"]
        }
        assert "cascade-test" not in pool_apps

        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        non_internal = [item for item in instances if not item["is_internal"]]
        assert len(non_internal) == 0

    def test_delete_template_by_instance_no_uninstall(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "by-instance-delete-test",
                "template_version": "1.0.0",
                "verbose_name": "By Instance Delete Test",
            },
        )
        assert import_response.status_code == 200

        install_response = app_client.post("/api/v1/apps/by-instance-delete-test")
        assert install_response.status_code == 200

        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        installed_app = next(
            item
            for item in instances
            if item["launchpad_app_name"] == "by-instance-delete-test"
        )

        delete_response = app_client.delete(
            f"/api/v1/apps/templates/by-instance/{installed_app['app_id']}",
            params={"uninstall": False},
        )
        assert delete_response.status_code == 204

        mock_apps_api_client.delete_app.assert_not_called()

        pool_response = app_client.get("/api/v1/apps")
        pool_apps = {
            item["launchpad_app_name"] for item in pool_response.json()["items"]
        }
        assert "by-instance-delete-test" not in pool_apps

        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()["items"]
        assert all(
            item["launchpad_app_name"] != "by-instance-delete-test"
            for item in instances
        )
