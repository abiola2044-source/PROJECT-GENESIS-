import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path("civilization_history.log")

def setup_logging(level=logging.INFO, max_bytes=5_000_000, backup_count=3):
    logger = logging.getLogger("project_genesis")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler
    fh = RotatingFileHandler(LOG_FILE, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

def get_logger():
    return setup_logging()