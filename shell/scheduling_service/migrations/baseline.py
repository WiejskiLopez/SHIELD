from __future__ import annotations

from pathlib import Path

from shell.platform.infrastructure.persistence.alembic_runner import (
    run_service_baseline,
)

_MIGRATIONS_DIR = Path(__file__).resolve().parent


async def run_scheduling_baseline(url: str, reset_db: bool = False) -> None:
    await run_service_baseline(
        url=url,
        migrations_dir=_MIGRATIONS_DIR,
        service_package="shell.scheduling_service",
        base_class="SchedulingSqlAlchemyModelBase",
        reset_db=reset_db,
    )
