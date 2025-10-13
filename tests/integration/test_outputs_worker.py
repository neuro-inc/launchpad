"""Integration tests for the post-outputs worker functionality"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


class TestOutputsWorker:
    """Tests for the output buffer and periodic worker"""

    async def test_app_added_to_buffer_on_install(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that installing an app adds it to the output buffer"""
        # Import a template first
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "test-template",
                "template_version": "1.0.0",
            },
        )

        # Install the app
        response = app_client.post("/api/v1/apps/test-template")
        assert response.status_code == 200

        # Access the app service from the test client's app
        from launchpad.app import Launchpad

        app: Launchpad = app_client.app  # type: ignore[assignment]
        app_service = app.app_service

        # Verify the buffer is not empty
        assert not app_service._output_buffer.empty()

    async def test_process_output_buffer_updates_outputs(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that process_output_buffer calls update_outputs with correct data"""
        # Set up mock to return existing outputs
        mock_apps_api_client.get_outputs.return_value = {
            "installed_apps": {"app_list": []}
        }

        # Import and install an app
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "test-template",
                "template_version": "1.0.0",
            },
        )

        install_response = app_client.post("/api/v1/apps/test-template")
        assert install_response.status_code == 200
        installed_data = install_response.json()

        # Access the app service
        from launchpad.app import Launchpad

        app: Launchpad = app_client.app  # type: ignore[assignment]
        app_service = app.app_service

        # Process the output buffer
        await app_service.process_output_buffer()

        # Verify buffer is now empty
        assert app_service._output_buffer.empty()

        # Verify update_outputs was called
        assert mock_apps_api_client.update_outputs.called
        call_args = mock_apps_api_client.update_outputs.call_args

        # Get the updated outputs
        assert call_args is not None
        updated_outputs = call_args[0][1]

        # Verify the app was added to installed_apps
        assert "installed_apps" in updated_outputs
        app_list = updated_outputs["installed_apps"]["app_list"]

        # Verify our app is in the list (internal apps may also be present)
        app_names = [app["app_name"] for app in app_list]
        assert installed_data["launchpad_app_name"] in app_names

    async def test_process_output_buffer_batch_processes_multiple_apps(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that multiple apps are processed in a single batch"""
        # Set up mock to return existing outputs
        mock_apps_api_client.get_outputs.return_value = {
            "installed_apps": {"app_list": []}
        }

        # Import and install multiple apps
        for i in range(3):
            app_client.post(
                "/api/v1/apps/templates/import",
                json={
                    "template_name": f"test-template-{i}",
                    "template_version": "1.0.0",
                    "name": f"test-app-{i}",
                },
            )
            install_response = app_client.post(f"/api/v1/apps/test-app-{i}")
            assert install_response.status_code == 200

        # Access the app service
        from launchpad.app import Launchpad

        app: Launchpad = app_client.app  # type: ignore[assignment]
        app_service = app.app_service

        # Process the output buffer
        await app_service.process_output_buffer()

        # Verify buffer is empty
        assert app_service._output_buffer.empty()

        # Verify update_outputs was called only once (batch processing)
        assert mock_apps_api_client.update_outputs.call_count == 1

        # Verify all apps were added
        call_args = mock_apps_api_client.update_outputs.call_args
        assert call_args is not None
        updated_outputs = call_args[0][1]
        app_list = updated_outputs["installed_apps"]["app_list"]

        # Verify all our test apps are present (internal apps may also be present)
        # Note: app_name in outputs comes from Apps API, which uses template_name
        app_names = {app["app_name"] for app in app_list}
        assert "test-template-0" in app_names
        assert "test-template-1" in app_names
        assert "test-template-2" in app_names

    async def test_process_output_buffer_retries_on_failure(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that apps are re-added to buffer if update_outputs fails"""
        # Set up mock to return existing outputs, then fail on update
        mock_apps_api_client.get_outputs.return_value = {
            "installed_apps": {"app_list": []}
        }
        mock_apps_api_client.update_outputs.side_effect = Exception(
            "Failed to update outputs"
        )

        # Import and install an app
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "test-template",
                "template_version": "1.0.0",
            },
        )
        app_client.post("/api/v1/apps/test-template")

        # Access the app service
        from launchpad.app import Launchpad

        app: Launchpad = app_client.app  # type: ignore[assignment]
        app_service = app.app_service

        # Get buffer size before processing (includes internal apps + our test app)
        initial_size = app_service._output_buffer.qsize()
        assert initial_size >= 1

        # Process the output buffer (should fail and re-add)
        await app_service.process_output_buffer()

        # Verify apps are back in buffer for retry
        assert app_service._output_buffer.qsize() == initial_size

    async def test_process_output_buffer_skips_duplicates(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that duplicate apps are not added to outputs"""
        # Install an app
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "test-template",
                "template_version": "1.0.0",
            },
        )
        install_response = app_client.post("/api/v1/apps/test-template")
        assert install_response.status_code == 200

        # Get the app_id from the install_app mock call
        install_call_args = mock_apps_api_client.install_app.call_args_list
        # Find the call for test-template
        test_app_id = None
        for call in install_call_args:
            payload = call[1]["payload"] if call[1] else call[0][0]
            if payload.get("template_name") == "test-template":
                # Get the response from the side_effect
                test_app_id = mock_apps_api_client.install_app.side_effect(payload)[
                    "id"
                ]
                break

        assert test_app_id is not None

        # Set up mock to return outputs with this app already present
        mock_apps_api_client.get_outputs.return_value = {
            "installed_apps": {
                "app_list": [
                    {
                        "app_id": str(test_app_id),
                        "app_name": "test-template",
                    }
                ]
            }
        }

        # Access the app service
        from launchpad.app import Launchpad

        app: Launchpad = app_client.app  # type: ignore[assignment]
        app_service = app.app_service

        # Process the output buffer
        await app_service.process_output_buffer()

        # Verify update_outputs was called
        assert mock_apps_api_client.update_outputs.called
        call_args = mock_apps_api_client.update_outputs.call_args
        assert call_args is not None

        # Verify the app_list still has only 1 instance of this app (no duplicate)
        updated_outputs = call_args[0][1]
        app_list = updated_outputs["installed_apps"]["app_list"]

        # Count how many times our test app appears
        test_app_count = sum(
            1 for a in app_list if str(a["app_id"]) == str(test_app_id)
        )
        assert test_app_count == 1

    async def test_process_output_buffer_empty_buffer(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that processing an empty buffer is a no-op"""
        # Access the app service
        from launchpad.app import Launchpad

        app: Launchpad = app_client.app  # type: ignore[assignment]
        app_service = app.app_service

        # Ensure buffer is empty
        assert app_service._output_buffer.empty()

        # Process the empty buffer
        await app_service.process_output_buffer()

        # Verify update_outputs was NOT called
        assert not mock_apps_api_client.update_outputs.called

    async def test_process_output_buffer_preserves_existing_apps(
        self, app_client: TestClient, mock_apps_api_client: AsyncMock
    ) -> None:
        """Test that existing apps in outputs are preserved when adding new apps"""
        existing_app_id = uuid4()

        # Set up mock with existing apps
        mock_apps_api_client.get_outputs.return_value = {
            "installed_apps": {
                "app_list": [
                    {
                        "app_id": str(existing_app_id),
                        "app_name": "existing-app",
                    }
                ]
            }
        }

        # Install a new app
        app_client.post(
            "/api/v1/apps/templates/import",
            json={
                "template_name": "new-template",
                "template_version": "1.0.0",
                "name": "new-app",
            },
        )
        app_client.post("/api/v1/apps/new-app")

        # Access the app service
        from launchpad.app import Launchpad

        app: Launchpad = app_client.app  # type: ignore[assignment]
        app_service = app.app_service

        # Process the output buffer
        await app_service.process_output_buffer()

        # Verify update_outputs was called
        call_args = mock_apps_api_client.update_outputs.call_args
        assert call_args is not None

        # Verify both apps are in the output (internal apps may also be present)
        updated_outputs = call_args[0][1]
        app_list = updated_outputs["installed_apps"]["app_list"]

        # Verify both app names are present
        app_names = {app["app_name"] for app in app_list}
        assert "existing-app" in app_names
        assert "new-template" in app_names  # Note: uses template_name not custom name

        # Verify the existing app ID is preserved
        app_ids = {app["app_id"] for app in app_list}
        assert str(existing_app_id) in app_ids
