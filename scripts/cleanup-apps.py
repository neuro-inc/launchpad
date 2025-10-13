#!/usr/bin/env python3
"""
Cleanup script for uninstalling all apps managed by Launchpad.
This script is intended to run as a Kubernetes Job with ArgoCD PostDelete hook.

Note: This script does NOT use the database since it will be deleted before this hook runs.
Instead, it fetches the list of installed apps from the Launchpad app outputs.
"""

import asyncio
import json
import logging
import os
import sys
from base64 import b64decode
from uuid import UUID

import aiohttp
from yarl import URL

# Import existing API client
from launchpad.ext.apps_api import AppsApiClient, AppsApiError, NotFound


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds
RETRY_BACKOFF = 2  # exponential backoff multiplier


class CleanupError(Exception):
    """Base exception for cleanup errors"""

    pass


async def get_installed_apps_from_outputs(
    api_client: AppsApiClient,
    launchpad_app_id: UUID,
) -> list[dict[str, str]]:
    """
    Fetch installed apps from Launchpad app outputs.
    Returns list of dicts with 'app_id' and 'app_name' keys.
    """
    logger.info(f"Fetching outputs for Launchpad app {launchpad_app_id}")

    try:
        outputs = await api_client.get_outputs(launchpad_app_id)
    except NotFound:
        logger.warning(f"Launchpad app {launchpad_app_id} not found or has no outputs")
        return []
    except AppsApiError as e:
        logger.error(f"Failed to fetch outputs for {launchpad_app_id}: {e}")
        raise CleanupError("Failed to fetch Launchpad app outputs") from e

    installed_apps = outputs.get("installed_apps", {})
    app_list = installed_apps.get("app_list", [])

    logger.info(f"Found {len(app_list)} apps in outputs")
    for app in app_list:
        logger.info(f"  - {app.get('app_name')} ({app.get('app_id')})")

    return app_list


def get_app_dependencies() -> dict[str, list[str]]:
    """
    Define app dependencies.
    Returns dict where key depends on values (must be deleted after values are deleted).
    """
    # OpenWebUI depends on postgres, vllm, and embeddings
    # So OpenWebUI must be deleted first
    return {
        "openwebui": ["postgres", "vllm-llama-3.1-8b", "embeddings"],
    }


def order_apps_for_deletion(apps: list[dict[str, str]]) -> list[list[UUID]]:
    """
    Order apps for deletion based on dependencies.
    Returns a list of lists, where each inner list contains app IDs that can be deleted in parallel.

    Dependency order:
    1. Apps that depend on others (openwebui) - must be deleted first
    2. Apps that are dependencies (postgres, vllm, embeddings) - can be deleted in parallel
    """
    dependencies = get_app_dependencies()

    # Build name -> app_id mapping
    name_to_app = {app["app_name"]: UUID(app["app_id"]) for app in apps}

    # Separate apps with dependencies from those without
    apps_with_deps = []
    apps_without_deps = []

    for app_name, app_id in name_to_app.items():
        if app_name in dependencies:
            apps_with_deps.append(app_id)
        else:
            apps_without_deps.append(app_id)

    # Return batches: first apps with dependencies, then apps without
    batches = []
    if apps_with_deps:
        batches.append(apps_with_deps)
    if apps_without_deps:
        batches.append(apps_without_deps)

    return batches


async def can_uninstall_app(api_client: AppsApiClient, app_id: UUID) -> bool:
    """
    Check if an app can be uninstalled.
    Returns True if the app exists and is not in 'uninstalling' or 'uninstalled' state.
    """
    try:
        response = await api_client.get_by_id(app_id)
        state = response.get("state", "").lower()

        if state in ("uninstalling", "uninstalled"):
            logger.info(f"App {app_id} is already {state}, skipping")
            return False

        logger.info(f"App {app_id} is in state '{state}', can uninstall")
        return True
    except NotFound:
        logger.info(f"App {app_id} not found in Apps API, already deleted")
        return False
    except AppsApiError as e:
        logger.warning(f"Error checking app {app_id} status: {e}")
        # Assume we can try to uninstall if we can't check status
        return True


async def uninstall_app_with_retry(api_client: AppsApiClient, app_id: UUID) -> None:
    """
    Attempt to uninstall an app with retry logic.
    Raises CleanupError if all retries fail.
    """
    # First check if we can uninstall
    if not await can_uninstall_app(api_client, app_id):
        return

    delay = RETRY_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"Attempting to uninstall {app_id} (attempt {attempt}/{MAX_RETRIES})"
            )
            await api_client.delete_app(app_id)
            logger.info(f"Successfully uninstalled {app_id}")
            return
        except NotFound:
            logger.info(f"App {app_id} not found, already deleted")
            return
        except AppsApiError as e:
            if attempt < MAX_RETRIES:
                logger.warning(
                    f"Failed to uninstall {app_id}: {e}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= RETRY_BACKOFF
            else:
                logger.error(
                    f"Failed to uninstall {app_id} after {MAX_RETRIES} attempts"
                )
                raise CleanupError(f"Failed to uninstall {app_id}") from e


async def delete_app_batch(
    app_ids: list[UUID],
    api_client: AppsApiClient,
) -> tuple[list[UUID], list[tuple[UUID, Exception]]]:
    """
    Delete a batch of apps in parallel with retry logic.
    Returns tuple of (successful_deletions, failed_deletions)
    """
    tasks = []
    for app_id in app_ids:
        tasks.append(uninstall_app_with_retry(api_client, app_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = []
    failed = []

    for app_id, result in zip(app_ids, results):
        if isinstance(result, Exception):
            failed.append((app_id, result))
            logger.error(f"Failed to delete {app_id}: {result}")
        else:
            successful.append(app_id)
            logger.info(f"Successfully deleted {app_id}")

    return successful, failed


async def cleanup_apps() -> int:
    """
    Main cleanup function.
    Returns 0 on success, 1 on failure.
    """
    logger.info("Starting app cleanup process")

    # Load configuration from environment
    try:
        apolo_config_b64 = os.environ["APOLO_PASSED_CONFIG"]
        apolo_config = json.loads(b64decode(apolo_config_b64))

        cluster = apolo_config["cluster"]
        org_name = apolo_config["org_name"]
        project_name = apolo_config["project_name"]
        token = apolo_config["token"]

        # Construct Apps API URL
        url = URL(apolo_config["url"])
        apps_api_url = f"{url.scheme}://{url.host}/apis/apps"

        # Get Launchpad app ID
        launchpad_app_id_str = os.environ.get("LAUNCHPAD_APP_ID")
        if not launchpad_app_id_str:
            logger.error("LAUNCHPAD_APP_ID environment variable is not set")
            return 1

        launchpad_app_id = UUID(launchpad_app_id_str)

    except KeyError as e:
        logger.error(f"Missing required environment variable: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Invalid LAUNCHPAD_APP_ID format: {e}")
        return 1

    try:
        # Create Apps API client using existing implementation
        async with aiohttp.ClientSession() as http:
            api_client = AppsApiClient(
                http=http,
                base_url=apps_api_url,
                token=token,
                cluster=cluster,
                org_name=org_name,
                project_name=project_name,
            )

            # Fetch installed apps from Launchpad app outputs
            apps = await get_installed_apps_from_outputs(api_client, launchpad_app_id)

            if not apps:
                logger.info("No apps to clean up")
                return 0

            logger.info(f"Found {len(apps)} apps to uninstall")

            # Order apps for deletion
            deletion_batches = order_apps_for_deletion(apps)
            logger.info(f"Apps will be deleted in {len(deletion_batches)} batches")

            # Delete apps in batches
            total_failed = []
            for batch_num, batch in enumerate(deletion_batches, 1):
                logger.info(
                    f"Processing batch {batch_num}/{len(deletion_batches)} ({len(batch)} apps)"
                )
                successful, failed = await delete_app_batch(batch, api_client)
                total_failed.extend(failed)

                if failed:
                    logger.warning(f"Batch {batch_num} had {len(failed)} failures")

            # Report final status
            if total_failed:
                logger.error(f"Cleanup completed with {len(total_failed)} failures:")
                for app_id, error in total_failed:
                    logger.error(f"  - {app_id}: {error}")
                return 1

            logger.info("All apps successfully uninstalled")
            return 0

    except Exception as e:
        logger.exception(f"Unexpected error during cleanup: {e}")
        return 1


def main() -> int:
    """Entry point"""
    try:
        return asyncio.run(cleanup_apps())
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())
