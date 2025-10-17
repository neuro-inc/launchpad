from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient


class TestTemplateImport:
    """Integration tests for template import functionality"""

    def test_import_template_minimal(self, app_client: TestClient) -> None:
        """Test importing a template with minimal parameters"""
        response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "my-template",
                "template_version": "1.0.0",
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 but got {response.status_code}: {response.json()}"
        data = response.json()

        # Verify template was created with API metadata
        assert data["name"] == "my-template"
        assert data["template_name"] == "my-template"
        assert data["template_version"] == "1.0.0"
        assert data["verbose_name"] == "my-template v1.0.0"  # From API template title
        assert data["description_short"] == "Short description from Apps API"
        assert data["logo"] == "https://example.com/logo.png"
        assert data["is_shared"] is True  # Default value
        assert data["is_internal"] is False  # Default value

    def test_import_template_with_overrides(self, app_client: TestClient) -> None:
        """Test importing a template with custom metadata overrides"""
        response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "custom-template",
                "template_version": "2.0.0",
                "name": "my-custom-name",
                "verbose_name": "My Custom Template",
                "description_short": "Custom short description",
                "description_long": "Custom long description",
                "logo": "https://mycustom.com/logo.png",
                "is_shared": False,  # Override to non-shared
                "is_internal": True,
                "tags": ["custom", "test"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify overrides take precedence
        assert data["name"] == "my-custom-name"
        assert data["verbose_name"] == "My Custom Template"
        assert data["description_short"] == "Custom short description"
        assert data["description_long"] == "Custom long description"
        assert data["logo"] == "https://mycustom.com/logo.png"
        assert data["is_shared"] is False  # Custom value
        assert data["is_internal"] is True
        assert "custom" in data["tags"]

    def test_import_template_upsert(self, app_client: TestClient) -> None:
        """Test that importing same template twice updates it"""
        # First import
        response1 = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "upsert-test",
                "template_version": "1.0.0",
                "verbose_name": "First Import",
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["verbose_name"] == "First Import"

        # Second import with same name
        response2 = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "upsert-test",
                "template_version": "2.0.0",  # Different version
                "verbose_name": "Second Import",
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["verbose_name"] == "Second Import"
        assert data2["template_version"] == "2.0.0"  # Updated

    def test_import_template_cannot_modify_is_internal_with_instances(
        self, app_client: TestClient
    ) -> None:
        """Test that is_internal cannot be modified when template has instances"""
        # First, import a template
        response1 = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "safety-test",
                "template_version": "1.0.0",
                "name": "safety-test-app",
                "is_internal": False,
            },
        )
        assert response1.status_code == 200

        # Install an instance from this template
        install_response = app_client.post(
            "/api/v1/apps/install",
            json={
                "template_name": "safety-test",
                "template_version": "1.0.0",
                "inputs": {"displayName": "Safety Test"},
                "name": "safety-test-app",
            },
        )
        assert install_response.status_code == 200

        # Try to update is_internal - should fail
        response2 = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "safety-test",
                "template_version": "1.0.0",
                "name": "safety-test-app",
                "is_internal": True,  # Trying to change this
            },
        )
        assert response2.status_code == 400
        error_response = response2.json()
        # The error detail is nested: {'detail': {'message': '...'}}
        assert "Cannot modify is_internal" in error_response["detail"]["message"]

    def test_import_template_cannot_modify_is_shared_with_instances(
        self, app_client: TestClient
    ) -> None:
        """Test that is_shared cannot be modified when template has instances"""
        # First, import a template
        response1 = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "shared-test",
                "template_version": "1.0.0",
                "name": "shared-test-app",
                "is_shared": True,
            },
        )
        assert response1.status_code == 200

        # Install an instance from this template
        install_response = app_client.post(
            "/api/v1/apps/install",
            json={
                "template_name": "shared-test",
                "template_version": "1.0.0",
                "inputs": {"displayName": "Shared Test"},
                "name": "shared-test-app",
            },
        )
        assert install_response.status_code == 200

        # Try to update is_shared - should fail
        response2 = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "shared-test",
                "template_version": "1.0.0",
                "name": "shared-test-app",
                "is_shared": False,  # Trying to change this
            },
        )
        assert response2.status_code == 400
        error_response = response2.json()
        # The error detail is nested: {'detail': {'message': '...'}}
        assert "Cannot modify is_shared" in error_response["detail"]["message"]

    def test_import_template_with_input(self, app_client: TestClient) -> None:
        """Test importing a template with input"""
        response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "service-deployment",
                "template_version": "1.0.0",
                "name": "custom-service",
                "verbose_name": "Custom Service Deployment",
                "input": {
                    "displayName": "My Service",
                    "preset": {"name": "cpu-small"},
                },
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200 but got {response.status_code}: {response.json()}"
        data = response.json()

        # Verify template was created
        assert data["name"] == "custom-service"
        assert data["template_name"] == "service-deployment"
        assert data["verbose_name"] == "Custom Service Deployment"

        # Verify the template is in the app pool (since it's not internal)
        pool_response = app_client.get("/api/v1/apps")
        assert pool_response.status_code == 200
        pool_data = pool_response.json()

        # Find our template in the pool
        custom_service = next(
            (
                item
                for item in pool_data["items"]
                if item["launchpad_app_name"] == "custom-service"
            ),
            None,
        )
        assert custom_service is not None
        assert custom_service["title"] == "Custom Service Deployment"


class TestAppImport:
    """Integration tests for app import functionality"""

    def test_import_app_minimal(self, app_client: TestClient) -> None:
        """Test importing an externally installed app"""
        app_id = uuid4()

        response = app_client.post(
            "/api/v1/apps/import",
            json={
                "app_id": str(app_id),
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify app was linked
        assert data["launchpad_app_name"] == "test-template"  # From template_name
        assert data["is_shared"] is True  # Always true for imported apps
        assert data["user_id"] is None

    def test_import_app_with_overrides(self, app_client: TestClient) -> None:
        """Test importing app with custom metadata"""
        app_id = uuid4()

        response = app_client.post(
            "/api/v1/apps/import",
            json={
                "app_id": str(app_id),
                "name": "my-imported-app",  # This is ignored - template_name from API is used
                "verbose_name": "My Imported App",
                "description_short": "Custom imported app",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # The 'name' parameter is ignored for app imports to prevent bugs
        # The template is always identified by template_name from Apps API
        assert (
            data["launchpad_app_name"] == "test-template"
        )  # From Apps API, not "my-imported-app"
        assert data["is_shared"] is True  # Always true for imported apps


class TestGenericAppInstall:
    """Integration tests for generic app installation"""

    def test_install_generic_app(self, app_client: TestClient) -> None:
        """Test installing a generic app with custom configuration"""
        response = app_client.post(
            "/api/v1/apps/install",
            json={
                "template_name": "generic-template",
                "template_version": "1.0.0",
                "inputs": {
                    "displayName": "My Generic App",
                    "preset": {"name": "cpu-small"},
                },
                "name": "my-generic-app",
                "verbose_name": "My Generic Application",
                "description_short": "A custom generic app",
                "logo": "https://example.com/custom-logo.png",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify app was installed
        assert data["launchpad_app_name"] == "my-generic-app"


class TestHandlerAppInstall:
    """Integration tests for installing apps with built-in handler classes"""

    def test_install_openwebui_app(self, app_client: TestClient) -> None:
        """Test installing OpenWebUI app with OpenWebUIApp handler"""
        # First, install the required dependencies
        # Install vLLM
        vllm_response = app_client.post("/api/v1/apps/vllm-llama-3.1-8b")
        assert vllm_response.status_code == 200

        # Install embeddings
        embeddings_response = app_client.post("/api/v1/apps/embeddings")
        assert embeddings_response.status_code == 200

        # Install postgres
        postgres_response = app_client.post("/api/v1/apps/postgres")
        assert postgres_response.status_code == 200

        # Now install OpenWebUI
        response = app_client.post("/api/v1/apps/openwebui")

        assert (
            response.status_code == 200
        ), f"Expected 200 but got {response.status_code}: {response.json()}"
        data = response.json()

        # Verify app was installed with correct name
        assert data["launchpad_app_name"] == "openwebui"
        assert data["is_shared"] is True


class TestAppPool:
    """Integration tests for app pool listing"""

    def test_get_apps_pool_empty(self, app_client: TestClient) -> None:
        """Test getting app pool with only seeded templates (OpenWebUI)"""
        response = app_client.get("/api/v1/apps")

        assert response.status_code == 200
        data = response.json()

        # Should return OpenWebUI which is seeded on startup
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["launchpad_app_name"] == "openwebui"
        assert data["items"][0]["title"] == "OpenWebUI"

    def test_get_apps_pool_with_templates(self, app_client: TestClient) -> None:
        """Test getting app pool after importing templates"""
        # Import a template first
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "pool-test",
                "template_version": "1.0.0",
                "verbose_name": "Pool Test Template",
            },
        )
        assert import_response.status_code == 200

        # Get app pool
        response = app_client.get("/api/v1/apps")

        assert response.status_code == 200
        data = response.json()

        # Should return OpenWebUI (seeded) + imported template
        assert "items" in data
        assert len(data["items"]) == 2

        # Get template names
        template_names = {item["launchpad_app_name"] for item in data["items"]}
        assert "openwebui" in template_names
        assert "pool-test" in template_names

    def test_get_apps_pool_excludes_internal(self, app_client: TestClient) -> None:
        """Test that internal templates are excluded from app pool"""
        # Import an internal template
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "internal-template",
                "template_version": "1.0.0",
                "is_internal": True,
            },
        )

        # Import a non-internal template
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "public-template",
                "template_version": "1.0.0",
                "is_internal": False,
            },
        )

        # Get app pool
        response = app_client.get("/api/v1/apps")

        assert response.status_code == 200
        data = response.json()

        # Should return OpenWebUI (seeded) + public-template, but NOT internal templates
        # Note: We also seed 3 internal apps (vllm, postgres, embeddings) which should be excluded
        assert len(data["items"]) == 2

        # Verify only non-internal templates are returned
        template_names = {item["launchpad_app_name"] for item in data["items"]}
        assert "openwebui" in template_names
        assert "public-template" in template_names
        # Internal template should NOT be in the pool
        assert "internal-template" not in template_names


class TestUnimportedInstances:
    """Integration tests for listing unimported app instances"""

    def test_get_unimported_instances_empty(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test getting unimported instances when Apps API returns empty list"""
        # Mock Apps API to return empty list
        mock_apps_api_client.list_instances.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "size": 50,
            "pages": 0,
        }

        response = app_client.get("/api/v1/apps/instances/unimported")

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    def test_get_unimported_instances_all_unimported(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test getting unimported instances when no apps are imported"""
        # Mock Apps API to return only healthy instances (API filters by states=["healthy"])
        mock_instances = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "app-1",
                "template_name": "jupyter",
                "template_version": "1.0.0",
                "display_name": "Jupyter Notebook",
                "state": "healthy",
            },
        ]
        mock_apps_api_client.list_instances.return_value = {
            "items": mock_instances,
            "total": 1,
            "page": 1,
            "size": 50,
            "pages": 1,
        }

        response = app_client.get("/api/v1/apps/instances/unimported")

        assert response.status_code == 200
        data = response.json()

        # Verify API was called with states filter
        mock_apps_api_client.list_instances.assert_called_once_with(
            page=1, size=50, states=["healthy"]
        )

        # All healthy instances should be returned since none are imported
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["name"] == "app-1"
        assert data["items"][0]["state"] == "healthy"

    def test_get_unimported_instances_filtered(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that imported instances are filtered out (API filters non-healthy)"""
        app_id_1 = "123e4567-e89b-12d3-a456-426614174000"
        app_id_2 = "223e4567-e89b-12d3-a456-426614174000"

        # Import one app
        import_response = app_client.post(
            "/api/v1/apps/import",
            json={"app_id": app_id_2},
        )
        assert import_response.status_code == 200

        # Mock Apps API to return only healthy instances (API filters by states=["healthy"])
        # Degraded instances won't be returned by the API anymore
        mock_instances = [
            {
                "id": app_id_1,
                "name": "app-1",
                "template_name": "jupyter",
                "template_version": "1.0.0",
                "display_name": "Jupyter Notebook",
                "state": "healthy",
            },
            {
                "id": app_id_2,  # This one is imported
                "name": "app-2",
                "template_name": "test-template",
                "template_version": "1.0.0",
                "display_name": "Test App",
                "state": "healthy",
            },
        ]
        mock_apps_api_client.list_instances.return_value = {
            "items": mock_instances,
            "total": 2,
            "page": 1,
            "size": 50,
            "pages": 1,
        }

        response = app_client.get("/api/v1/apps/instances/unimported")

        assert response.status_code == 200
        data = response.json()

        # Verify API was called with states filter
        mock_apps_api_client.list_instances.assert_called_once_with(
            page=1, size=50, states=["healthy"]
        )

        # Only 1 instance should be returned (app-1: healthy and unimported)
        # app-2 is excluded (imported)
        # app-3 would have been excluded by the API (degraded, filtered by states=["healthy"])
        assert len(data["items"]) == 1
        assert data["total"] == 1

        # Verify only the healthy, unimported instance is returned
        returned_ids = [item["id"] for item in data["items"]]
        assert app_id_1 in returned_ids
        assert app_id_2 not in returned_ids  # Imported app should be filtered out

    def test_get_unimported_instances_pagination(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test pagination parameters are passed to Apps API"""
        mock_apps_api_client.list_instances.return_value = {
            "items": [],
            "total": 0,
            "page": 2,
            "size": 10,
            "pages": 0,
        }

        response = app_client.get("/api/v1/apps/instances/unimported?page=2&size=10")

        assert response.status_code == 200
        # Verify that pagination parameters and states filter were passed to Apps API
        mock_apps_api_client.list_instances.assert_called_once_with(
            page=2, size=10, states=["healthy"]
        )
