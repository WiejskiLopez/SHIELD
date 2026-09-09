"""SQLite fixtures for scheduling integration tests."""

from __future__ import annotations

import pytest

from shell.tests.shared.db import build_db_url


@pytest.fixture(scope="module")
def database_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    return build_db_url(tmp_path_factory, subdir="scheduling", db_name="test.db")
