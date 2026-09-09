from __future__ import annotations

from shell.ingestion_service.infrastructure.ingestion.seed.dev import seed_dev_sync
from shell.ingestion_service.migrations.baseline import run_ingestion_baseline
from shell.platform.application.ports.runtime.seed import SeedProvider
from shell.platform.infrastructure.persistence.sql.seed_helpers import run_seed_into


class IngestionSeedProvider(SeedProvider):
    async def bootstrap_database(self, url: str, reset_db: bool = False) -> None:
        await bootstrap_ingestion_database(url, reset_db)

    async def seed_dev_data(self, url: str) -> None:
        await seed_ingestion_dev_data(url)


async def bootstrap_ingestion_database(url: str, reset_db: bool = False) -> None:
    await run_ingestion_baseline(url, reset_db=reset_db)


async def seed_ingestion_dev_data(url: str, reset_db: bool = False) -> None:
    await bootstrap_ingestion_database(url, reset_db=reset_db)
    await run_seed_into(url, seed_dev_sync)
