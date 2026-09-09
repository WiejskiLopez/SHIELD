"""Deprecated shim — import from shell.tests.shared.config instead.

Kept for one sprint to avoid breaking external branches.
"""

from __future__ import annotations

import warnings

from shell.tests.shared.config import resolve_test_db_dir

warnings.warn(
    "shell.tests.shared.test_config is deprecated; use shell.tests.shared.config instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["resolve_test_db_dir"]
