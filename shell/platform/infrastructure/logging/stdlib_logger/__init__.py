"""Structured JSON logger — implements the Logger port using stdlib logging."""

from __future__ import annotations

from shell.platform.infrastructure.context import (
    correlation_id_var,
    get_correlation_id,
    set_correlation_id,
)
from shell.platform.infrastructure.logging.stdlib_logger.json_formatter import JsonFormatter
from shell.platform.infrastructure.logging.stdlib_logger.stdlib_logger import (
    StdlibLogger,
)

__all__ = [
    "StdlibLogger",
    "JsonFormatter",
    "correlation_id_var",
    "get_correlation_id",
    "set_correlation_id",
]
