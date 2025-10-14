import uvicorn
from neuro_logging import init_logging

from launchpad.app_factory import create_app
from launchpad.config import EnvironConfigFactory


if __name__ == "__main__":
    # local run
    init_logging(health_check_url_path="/ping")
    config = EnvironConfigFactory().create()
    uvicorn.run(
        create_app(config=config),
        port=config.server.port,
        host=config.server.host,
        proxy_headers=True,
        log_config=None,
    )
