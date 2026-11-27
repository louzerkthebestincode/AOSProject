from __future__ import annotations

import logging
from pathlib import Path
import sys


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | PID:%(process)d | Thread:%(thread)d | %(message)s"


def configure_logging(log_path: str | Path = "logs/simulation.log", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("deadlock_simulator")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    try:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, mode="w", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.error(f"Task: Logging | Unavailable log file '{log_path}': {exc} | Code: 2")

    return logger
