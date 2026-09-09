"""Root conftest — global markers, hooks and disposal of tracked SQL session factories."""

from __future__ import annotations

import os

import pytest

from shell.tests.shared.sql_lifecycle import dispose_tracked_session_factories


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: fast unit tests, no external dependencies")
    config.addinivalue_line("markers", "integration: tests requiring database or external services")
    config.addinivalue_line("markers", "e2e: end-to-end tests via API or CLI")
    # Always report skip reasons (equivalent to -rs); pytest.ini already sets
    # -ra which is a superset, so this is a no-op guarantee, not a logic change.
    reportchars = config.option.reportchars or ""
    if "a" not in reportchars and "s" not in reportchars:
        config.option.reportchars = reportchars + "s"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("POSTGRES_TEST_URL") is None:
        skip_pg = pytest.mark.skip(reason="POSTGRES_TEST_URL not set")
        for item in items:
            if "sql_postgres" in str(item.fspath):
                item.add_marker(skip_pg)


__all__ = ["dispose_tracked_session_factories"]
