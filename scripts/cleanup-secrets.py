import asyncio
import logging
import os
import sys
from uuid import UUID

from apolo_app_types.outputs.utils.apolo_secrets import delete_apolo_secret
from apolo_apps_launchpad.outputs_processor import APP_SECRET_KEYS


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


async def delete_secret_with_retry(app_instance_id: str, secret_key: str) -> None:
    """
    Attempt to delete a secret with retry logic.
    Logs warnings on failure but does not raise exceptions.
    """
    delay = RETRY_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f'Attempting to delete secret "{secret_key}-{app_instance_id}" '
                f"(attempt {attempt}/{MAX_RETRIES})"
            )
            await delete_apolo_secret(app_instance_id=app_instance_id, key=secret_key)
            logger.info(f'Successfully deleted secret "{secret_key}-{app_instance_id}"')
            return
        except Exception as e:
            if attempt < MAX_RETRIES:
                logger.warning(
                    f'Failed to delete secret "{secret_key}-{app_instance_id}": {e}. '
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= RETRY_BACKOFF
            else:
                logger.error(
                    f'Failed to delete secret "{secret_key}-{app_instance_id}" '
                    f"after {MAX_RETRIES} attempts: {e}"
                )


async def cleanup_secrets():
    launchpad_app_id_str = os.environ.get("LAUNCHPAD_APP_ID")
    if not launchpad_app_id_str:
        err = "LAUNCHPAD_APP_ID must be provided"
        raise Exception(err)

    for secret_key in APP_SECRET_KEYS.values():
        await delete_secret_with_retry(
            app_instance_id=launchpad_app_id_str, secret_key=secret_key
        )


def main() -> int:
    """Entry point"""
    try:
        return asyncio.run(cleanup_secrets())
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())
