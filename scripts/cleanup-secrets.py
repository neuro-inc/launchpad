import asyncio
import logging
import os
import sys
from uuid import UUID

import backoff
from apolo_app_types.outputs.utils.apolo_secrets import delete_apolo_secret
from apolo_apps_launchpad.outputs_processor import APP_SECRET_KEYS


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@backoff.on_exception(
    backoff.expo,
    Exception,
    max_tries=5,
    base=2,
    factor=2,
    logger=logger,
)
async def delete_secret_with_retry(app_instance_id: str, secret_key: str) -> None:
    """
    Attempt to delete a secret with retry logic using exponential backoff.
    Retries up to 5 times with delays: 2s, 4s, 8s, 16s, 32s.
    Logs warnings on failure but does not raise exceptions on final failure.
    """
    logger.info(f'Deleting secret "{secret_key}-{app_instance_id}"')
    await delete_apolo_secret(app_instance_id=app_instance_id, key=secret_key)
    logger.info(f'Successfully deleted secret "{secret_key}-{app_instance_id}"')


async def cleanup_secrets():
    launchpad_app_id_str = os.environ.get("LAUNCHPAD_APP_ID")
    if not launchpad_app_id_str:
        err = "LAUNCHPAD_APP_ID must be provided"
        raise Exception(err)

    for secret_key in APP_SECRET_KEYS.values():
        try:
            await delete_secret_with_retry(
                app_instance_id=launchpad_app_id_str, secret_key=secret_key
            )
        except Exception as e:
            logger.error(
                f'Failed to delete secret "{secret_key}-{launchpad_app_id_str}" '
                f"after all retries: {e}"
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
