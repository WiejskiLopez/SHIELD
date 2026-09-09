from __future__ import annotations

from shell.platform.application.ports.runtime.seed import SeedProvider
from shell.platform.infrastructure.persistence.sql.seed_helpers import run_seed_into
from shell.project_service.infrastructure.project.seed.dev import seed_dev_sync
from shell.project_service.migrations.baseline import run_project_baseline


class ProjectSeedProvider(SeedProvider):
    async def bootstrap_database(self, url: str, reset_db: bool = False) -> None:
        await bootstrap_project_database(url, reset_db)

    async def seed_dev_data(self, url: str) -> None:
        await seed_project_dev_data(url)


async def bootstrap_project_database(url: str, reset_db: bool = False) -> None:
    await run_project_baseline(url, reset_db=reset_db)


async def seed_project_dev_data(url: str, reset_db: bool = False) -> None:
    await bootstrap_project_database(url, reset_db=reset_db)
    await run_seed_into(url, seed_dev_sync)
