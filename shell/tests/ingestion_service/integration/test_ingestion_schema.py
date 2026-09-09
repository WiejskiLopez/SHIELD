"""Integration coverage for the ingestion database baseline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from shell.ingestion_service.migrations.baseline import run_ingestion_baseline

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


async def _table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as connection:
        return set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))


async def test_ingestion_baseline_creates_delivery_tables(database_url: str) -> None:
    await run_ingestion_baseline(database_url)
    engine = create_async_engine(database_url)
    try:
        tables = await _table_names(engine)
    finally:
        await engine.dispose()

    assert {"event_inbox", "event_outbox", "command_inbox", "command_outbox"} <= tables
