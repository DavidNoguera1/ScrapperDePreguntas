import logging
import os
from datetime import datetime

from core.config import LOG_DIR


LOGGER = logging.getLogger(__name__)
LOG_FILE = None


def setup_logging():
    global LOG_FILE
    if LOG_FILE:
        return LOG_FILE

    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = os.path.join(LOG_DIR, f"scraper_{timestamp}.log")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    LOGGER.info("Log de ejecución: %s", LOG_FILE)
    return LOG_FILE
