from __future__ import annotations

from shell.platform.application.ports.runtime.seed import SeedProvider
from shell.platform.infrastructure.persistence.sql.seed_helpers import run_seed_into
from shell.session_service.infrastructure.session.seed.dev import seed_dev_sync
from shell.session_service.migrations.baseline import run_session_baseline


class SessionSeedProvider(SeedProvider):
    async def bootstrap_database(self, url: str, reset_db: bool = False) -> None:
        await bootstrap_session_database(url, reset_db)

    async def seed_dev_data(self, url: str) -> None:
        await seed_session_dev_data(url)


async def bootstrap_session_database(url: str, reset_db: bool = False) -> None:
    await run_session_baseline(url, reset_db=reset_db)


async def seed_session_dev_data(url: str, reset_db: bool = False) -> None:
    await bootstrap_session_database(url, reset_db=reset_db)
    await run_seed_into(url, seed_dev_sync)
