"""Konfiguracja logowania platformy (JSON formatter, stdout)."""

from __future__ import annotations

import logging
import sys

from shell.platform.infrastructure.logging.stdlib_logger import JsonFormatter


def setup_logging(level: str | int = logging.INFO) -> None:
    resolved_level = (
        logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        if isinstance(level, str)
        else level
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(
        level=resolved_level,
        handlers=[handler],
        force=True,
    )
