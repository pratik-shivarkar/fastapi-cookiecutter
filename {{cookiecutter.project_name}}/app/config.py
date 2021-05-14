import os
import logging

from pythonjsonlogger import jsonlogger


def parse_bool(value: str) -> bool:
    return value.lower() in ("yes", "true", "t", "1")


production_mode = parse_bool(os.getenv('PRODUCTION'))
list_of_origins = os.getenv('ORIGINS')
origins = []

logger = logging.getLogger()
logHandler = logging.StreamHandler()


if production_mode:
    # Setup Logger
    logger.setLevel(level=logging.WARNING)
    formatter = jsonlogger.JsonFormatter()
    logHandler.setFormatter(formatter)
    # Setup CORS Origin
    origins = list_of_origins.split(",")
else:
    # Setup Logger
    logger.setLevel(level=logging.DEBUG)
    # Setup Development Origins
    origins = [
        "http://localhost",
        "http://localhost:8000"
    ]

logger.addHandler(logHandler)
