"""Deprecated shim — import from shell.tests.shared.db instead.

Kept for one sprint to avoid breaking external branches.
"""

from __future__ import annotations

import warnings

from shell.tests.shared.db import build_db_url

warnings.warn(
    "shell.tests.shared.test_db is deprecated; use shell.tests.shared.db instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["build_db_url"]
