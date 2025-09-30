#!/usr/bin/env python3
"""
Cleanup script for uninstalling all apps managed by Launchpad.
This script is intended to run as a Kubernetes Job with ArgoCD PostDelete hook.
"""
import asyncio
import json
import logging
import os
import sys
from base64 import b64decode

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from yarl import URL

# Import existing models and functions
from launchpad.apps.models import InstalledApp
from launchpad.apps.storage import list_apps
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


def order_apps_for_deletion(apps: list[InstalledApp]) -> list[list[InstalledApp]]:
    """
    Order apps for deletion based on dependencies.
    Returns a list of lists, where each inner list contains apps that can be deleted in parallel.

    Dependency order:
    1. User-facing apps (openwebui) - must be deleted first
    2. Internal apps (postgres, vllm, embeddings) - can be deleted in parallel after user-facing apps
    """
    user_facing = []
    internal = []

    for app in apps:
        if app.is_internal:
            internal.append(app)
        else:
            user_facing.append(app)

    # Return batches: first user-facing apps, then internal apps
    batches = []
    if user_facing:
        batches.append(user_facing)
    if internal:
        batches.append(internal)

    return batches


async def can_uninstall_app(api_client: AppsApiClient, app: InstalledApp) -> bool:
    """
    Check if an app can be uninstalled.
    Returns True if the app exists and is not in 'uninstalling' or 'uninstalled' state.
    """
    try:
        response = await api_client.get_by_id(app.app_id)
        state = response.get("state", "").lower()

        if state in ("uninstalling", "uninstalled"):
            logger.info(f"App {app.launchpad_app_name} is already {state}, skipping")
            return False

        logger.info(f"App {app.launchpad_app_name} is in state '{state}', can uninstall")
        return True
    except NotFound:
        logger.info(f"App {app.launchpad_app_name} not found in Apps API, already deleted")
        return False
    except AppsApiError as e:
        logger.warning(f"Error checking app {app.launchpad_app_name} status: {e}")
        # Assume we can try to uninstall if we can't check status
        return True


async def uninstall_app_with_retry(api_client: AppsApiClient, app: InstalledApp) -> None:
    """
    Attempt to uninstall an app with retry logic.
    Raises CleanupError if all retries fail.
    """
    # First check if we can uninstall
    if not await can_uninstall_app(api_client, app):
        return

    delay = RETRY_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Attempting to uninstall {app.launchpad_app_name} (attempt {attempt}/{MAX_RETRIES})")
            await api_client.delete_app(app.app_id)
            logger.info(f"Successfully uninstalled {app.launchpad_app_name}")
            return
        except NotFound:
            logger.info(f"App {app.launchpad_app_name} not found, already deleted")
            return
        except AppsApiError as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"Failed to uninstall {app.launchpad_app_name}: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= RETRY_BACKOFF
            else:
                logger.error(f"Failed to uninstall {app.launchpad_app_name} after {MAX_RETRIES} attempts")
                raise CleanupError(f"Failed to uninstall {app.launchpad_app_name}") from e


async def delete_app_batch(
    apps: list[InstalledApp],
    api_client: AppsApiClient,
) -> tuple[list[InstalledApp], list[tuple[InstalledApp, Exception]]]:
    """
    Delete a batch of apps in parallel with retry logic.
    Returns tuple of (successful_deletions, failed_deletions)
    """
    tasks = []
    for app in apps:
        tasks.append(uninstall_app_with_retry(api_client, app))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = []
    failed = []

    for app, result in zip(apps, results):
        if isinstance(result, Exception):
            failed.append((app, result))
            logger.error(f"Failed to delete {app.launchpad_app_name}: {result}")
        else:
            successful.append(app)
            logger.info(f"Successfully deleted {app.launchpad_app_name}")

    return successful, failed


async def cleanup_apps() -> int:
    """
    Main cleanup function.
    Returns 0 on success, 1 on failure.
    """
    logger.info("Starting app cleanup process")

    # Load configuration from environment
    try:
        db_host = os.environ["DB_HOST"]
        db_user = os.environ["DB_USER"]
        db_password = os.environ["DB_PASSWORD"]
        db_name = os.environ["DB_NAME"]
        db_port = os.environ.get("DB_PORT", "5432")

        apolo_config_b64 = os.environ["APOLO_PASSED_CONFIG"]
        apolo_config = json.loads(b64decode(apolo_config_b64))

        cluster = apolo_config["cluster"]
        org_name = apolo_config["org_name"]
        project_name = apolo_config["project_name"]
        token = apolo_config["token"]

        # Construct Apps API URL
        url = URL(apolo_config["url"])
        apps_api_url = f"{url.scheme}://{url.host}/apis/apps"

    except KeyError as e:
        logger.error(f"Missing required environment variable: {e}")
        return 1

    # Create database connection
    postgres_dsn = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_async_engine(postgres_dsn, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Fetch all installed apps using existing storage function
            apps = list(await list_apps(session))

            if not apps:
                logger.info("No apps to clean up")
                return 0

            logger.info(f"Found {len(apps)} apps to uninstall")
            for app in apps:
                logger.info(f"  - {app.launchpad_app_name} ({app.app_id}) - internal={app.is_internal}")

            # Order apps for deletion
            deletion_batches = order_apps_for_deletion(apps)
            logger.info(f"Apps will be deleted in {len(deletion_batches)} batches")

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

                # Delete apps in batches
                total_failed = []
                for batch_num, batch in enumerate(deletion_batches, 1):
                    logger.info(f"Processing batch {batch_num}/{len(deletion_batches)} ({len(batch)} apps)")
                    successful, failed = await delete_app_batch(batch, api_client)
                    total_failed.extend(failed)

                    if failed:
                        logger.warning(f"Batch {batch_num} had {len(failed)} failures")

                # Report final status
                if total_failed:
                    logger.error(f"Cleanup completed with {len(total_failed)} failures:")
                    for app, error in total_failed:
                        logger.error(f"  - {app.launchpad_app_name} ({app.app_id}): {error}")
                    return 1

                logger.info("All apps successfully uninstalled")
                return 0

    except Exception as e:
        logger.exception(f"Unexpected error during cleanup: {e}")
        return 1
    finally:
        await engine.dispose()


def main() -> int:
    """Entry point"""
    try:
        return asyncio.run(cleanup_apps())
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())