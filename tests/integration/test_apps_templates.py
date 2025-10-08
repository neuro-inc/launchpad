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

    def test_import_template_with_handler_class(self, app_client: TestClient) -> None:
        """Test importing a template with a custom handler_class"""
        response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "service-deployment",
                "template_version": "1.0.0",
                "name": "custom-service",
                "verbose_name": "Custom Service Deployment",
                "handler_class": "ServiceDeploymentApp",
                "default_inputs": {
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
                "name": "my-imported-app",
                "verbose_name": "My Imported App",
                "description_short": "Custom imported app",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify custom name was used
        assert data["launchpad_app_name"] == "my-imported-app"
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
    """Integration tests for installing apps with custom handler classes"""

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

    def test_install_service_deployment_app(self, app_client: TestClient) -> None:
        """Test installing an app with ServiceDeploymentApp handler"""
        # First import a template with ServiceDeploymentApp handler
        import_response = app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "service-deployment",
                "template_version": "1.0.0",
                "name": "test-service",
                "verbose_name": "Test Service Deployment",
                "handler_class": "ServiceDeploymentApp",
                "default_inputs": {
                    "displayName": "Test Service",
                    "preset": {"name": "cpu-small"},
                },
            },
        )
        assert import_response.status_code == 200

        # Now install the app
        response = app_client.post("/api/v1/apps/test-service")

        assert (
            response.status_code == 200
        ), f"Expected 200 but got {response.status_code}: {response.json()}"
        data = response.json()

        # Verify app was installed
        assert data["launchpad_app_name"] == "test-service"
        assert data["is_shared"] is True

    def test_install_service_deployment_with_user_inputs(
        self, app_client: TestClient
    ) -> None:
        """Test installing ServiceDeploymentApp with user-provided inputs"""
        # Import template
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "service-deployment",
                "template_version": "1.0.0",
                "name": "custom-service",
                "handler_class": "ServiceDeploymentApp",
                "default_inputs": {
                    "displayName": "Default Service",
                    "preset": {"name": "cpu-small"},
                },
            },
        )

        # Install with custom inputs
        response = app_client.post(
            "/api/v1/apps/custom-service",
            json={
                "displayName": "Custom Display Name",
                "preset": {"name": "cpu-large"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["launchpad_app_name"] == "custom-service"

    def test_service_deployment_adds_middleware_to_payload(
        self, app_client: TestClient, mock_apps_api_client
    ) -> None:
        """Test that ServiceDeploymentApp adds ingress_middleware to the Apps API payload"""
        # Import template with ServiceDeploymentApp handler
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "service-deployment",
                "template_version": "1.0.0",
                "name": "middleware-test",
                "handler_class": "ServiceDeploymentApp",
                "default_inputs": {
                    "displayName": "Test Service",
                    "preset": {"name": "cpu-small"},
                },
            },
        )

        # Install the app
        response = app_client.post("/api/v1/apps/middleware-test")
        assert (
            response.status_code == 200
        ), f"Failed: {response.status_code} - {response.json()}"

        # Check that install_app was called with the correct payload
        mock_apps_api_client.install_app.assert_called()
        call_args = mock_apps_api_client.install_app.call_args

        # Extract the payload from the call
        payload = call_args[1]["payload"]  # kwargs

        # Print payload for debugging
        import json

        print("\n=== Apps API Payload ===")
        print(json.dumps(payload, indent=2))
        print("=== End Payload ===\n")

        # Verify the middleware config was added
        assert "input" in payload, "Payload missing 'input' field"
        inputs = payload["input"]
        assert (
            "networking_config" in inputs
        ), f"Inputs missing 'networking_config': {list(inputs.keys())}"
        assert (
            "advanced_networking" in inputs["networking_config"]
        ), f"networking_config missing 'advanced_networking': {list(inputs['networking_config'].keys())}"
        assert (
            "ingress_middleware" in inputs["networking_config"]["advanced_networking"]
        ), f"advanced_networking missing 'ingress_middleware': {list(inputs['networking_config']['advanced_networking'].keys())}"
        assert (
            inputs["networking_config"]["advanced_networking"]["ingress_middleware"][
                "name"
            ]
            == "test-middleware"
        ), f"Expected middleware name 'test-middleware' but got {inputs['networking_config']['advanced_networking']['ingress_middleware']['name']}"

        # Verify original inputs are preserved
        assert inputs["displayName"] == "Test Service"
        assert inputs["preset"]["name"] == "cpu-small"


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
