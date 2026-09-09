"""SQLite migration lifecycle tests for every bounded context."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import pytest

from shell.definition_service.migrations.baseline import run_definition_baseline
from shell.execution_service.migrations.baseline import run_execution_baseline
from shell.ingestion_service.migrations.baseline import run_ingestion_baseline
from shell.project_service.migrations.baseline import run_project_baseline
from shell.scheduling_service.migrations.baseline import run_scheduling_baseline
from shell.session_service.migrations.baseline import run_session_baseline
from shell.user_service.migrations.baseline import run_user_baseline

if TYPE_CHECKING:
    from pathlib import Path

_MigrationRunner = Callable[[str, bool], Awaitable[None]]

_MIGRATION_RUNNERS: tuple[tuple[str, _MigrationRunner], ...] = (
    ("definition", run_definition_baseline),
    ("execution", run_execution_baseline),
    ("ingestion", run_ingestion_baseline),
    ("project", run_project_baseline),
    ("scheduling", run_scheduling_baseline),
    ("session", run_session_baseline),
    ("user", run_user_baseline),
)


@pytest.mark.integration
async def test_each_service_migration_supports_upgrade_downgrade_upgrade(
    tmp_path: Path,
) -> None:
    for service_name, run_migrations in _MIGRATION_RUNNERS:
        database_url = f"sqlite+aiosqlite:///{tmp_path / f'{service_name}.db'}"

        await run_migrations(database_url)
        await run_migrations(database_url, reset_db=True)

        assert (tmp_path / f"{service_name}.db").exists()
