"""Tests for shared migration baseline orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from shell.platform.infrastructure.persistence import alembic_runner


@pytest.mark.asyncio
async def test_run_service_baseline_runs_platform_then_service_migrations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    platform = AsyncMock()
    service = AsyncMock()
    monkeypatch.setattr(alembic_runner, "run_platform_baseline", platform)
    monkeypatch.setattr(alembic_runner, "run_versioned_migrations", service)

    await alembic_runner.run_service_baseline(
        url="sqlite+aiosqlite:///test.db",
        migrations_dir=Path("migrations"),
        service_package="shell.example_service",
        base_class="ExampleSqlAlchemyModelBase",
        reset_db=True,
        include_saga=True,
    )

    platform.assert_awaited_once_with(
        url="sqlite+aiosqlite:///test.db",
        reset_db=True,
        include_saga=True,
    )
    service.assert_awaited_once_with(
        url="sqlite+aiosqlite:///test.db",
        migrations_dir=Path("migrations"),
        service_package="shell.example_service",
        base_class="ExampleSqlAlchemyModelBase",
        reset_db=True,
    )
    assert platform.await_args_list[0].kwargs["include_saga"] is True
