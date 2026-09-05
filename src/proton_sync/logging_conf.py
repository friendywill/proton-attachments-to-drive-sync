"""Logging setup. No prints anywhere else in this codebase."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(level: str, log_dir: str) -> None:
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    handlers: list[logging.Handler] = [logging.StreamHandler(stream=sys.stdout)]

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        Path(log_dir) / "proton-sync.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    handlers.append(file_handler)

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=handlers)
