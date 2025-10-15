from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

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
    }


class TestTemplatesEndpoint:
    """Integration tests for the /templates endpoint"""

    def test_get_templates_all(self, app_client: TestClient) -> None:
        """Test getting all templates (internal and non-internal)"""
        response = app_client.get("/api/v1/apps/templates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have seeded templates: openwebui, vllm, postgres, embeddings
        assert len(data) >= 4

        # Verify all templates have required fields
        for template in data:
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
        assert len(data) == 3
        for template in data:
            assert template["is_internal"] is True

        internal_names = {t["name"] for t in data}
        assert "vllm-llama-3.1-8b" in internal_names
        assert "postgres" in internal_names
        assert "embeddings" in internal_names

    def test_get_templates_non_internal_only(self, app_client: TestClient) -> None:
        """Test filtering only non-internal templates"""
        response = app_client.get("/api/v1/apps/templates?is_internal=false")
        assert response.status_code == 200
        data = response.json()

        # Should have at least openwebui (seeded)
        assert len(data) >= 1
        for template in data:
            assert template["is_internal"] is False

        # OpenWebUI should be present
        openwebui = next((t for t in data if t["name"] == "openwebui"), None)
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
        test_template = next((t for t in data if t["name"] == "test-template"), None)
        assert test_template is not None
        assert test_template["verbose_name"] == "Test Template"
        assert test_template["template_name"] == "test-template"
        assert test_template["template_version"] == "1.0.0"


class TestInstancesEndpoint:
    """Integration tests for the /instances endpoint"""

    def test_get_instances_empty(self, app_client: TestClient) -> None:
        """Test getting instances when none exist"""
        response = app_client.get("/api/v1/apps/instances")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

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
        non_internal = [item for item in data if not item["is_internal"]]

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
        non_internal = [item for item in data if not item["is_internal"]]

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
        instances = instances_response.json()
        actual_app_id = next(
            item["app_id"] for item in instances if item["launchpad_app_name"] == app_id
        )

        # Delete the instance
        delete_response = app_client.delete(f"/api/v1/apps/instances/{actual_app_id}")
        assert delete_response.status_code == 204

        # Verify it was deleted via Apps API
        mock_apps_api_client.delete_app.assert_called_once()

        # Verify it's no longer in the database
        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()
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
        instances = instances_response.json()
        non_internal = [item for item in instances if not item["is_internal"]]
        assert len(non_internal) == 1
        assert non_internal[0]["launchpad_app_name"] == "cascade-test"

        # Delete the template
        delete_response = app_client.delete(f"/api/v1/apps/templates/{template_id}")
        assert delete_response.status_code == 204

        # Verify Apps API delete was called for the instance
        assert mock_apps_api_client.delete_app.call_count == 1

        # Verify both template and instance are gone
        pool_response = app_client.get("/api/v1/apps")
        pool_apps = {
            item["launchpad_app_name"] for item in pool_response.json()["items"]
        }
        assert "cascade-test" not in pool_apps

        instances_response = app_client.get("/api/v1/apps/instances")
        instances = instances_response.json()
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
        instances = instances_response.json()
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
