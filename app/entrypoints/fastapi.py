import logging

import uvicorn

from app import config

logger = logging.getLogger(__name__)


def main() -> None:
    uvicorn.run(
        "app.infra.fastapi_app:app",
        host=config.config.host,
        port=config.config.port,
        log_config=config.config.log_config,
        reload=config.config.python_env == "development",
    )


if __name__ == "__main__":
    main()
