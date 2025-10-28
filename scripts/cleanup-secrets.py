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


async def cleanup_secrets():
    launchpad_app_id_str = os.environ.get("LAUNCHPAD_APP_ID")
    if not launchpad_app_id_str:
        err = "LAUNCHPAD_APP_ID must be provided"
        raise Exception(err)

    for secret_key in APP_SECRET_KEYS.values():
        try:
            await delete_apolo_secret(
                app_instance_id=launchpad_app_id_str, key=secret_key
            )
            logger.info(f'Deleted secret "{secret_key}-{launchpad_app_id_str}"')
        except Exception as e:
            logger.debug(e)


def main() -> int:
    """Entry point"""
    try:
        return asyncio.run(cleanup_secrets())
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())
