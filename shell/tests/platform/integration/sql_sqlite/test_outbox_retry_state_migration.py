"""Platform baseline migration test for the outbox retry-state columns.

Proves the ``platform_0009_outbox_retry_state`` migration applies on a fresh
database and that the ORM models round-trip the new columns on the migrated
schema (model ↔ migration sync for ``event_outbox`` / ``command_outbox``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import MetaData, inspect, select
from sqlalchemy.orm import DeclarativeBase

from shell.platform.domain.value_objects.outbox_status import OutboxStatus
from shell.platform.infrastructure.persistence.alembic_runner import (
    run_platform_baseline,
)
from shell.platform.infrastructure.persistence.sql import build_session_factory
from shell.platform.infrastructure.persistence.sql.models.command_delivery import (
    build_command_delivery_models,
)
from shell.platform.infrastructure.persistence.sql.models.event_delivery import (
    build_event_delivery_models,
)


class MigrationTestModelBase(DeclarativeBase):
    metadata = MetaData()


_EXPECTED_COLUMNS = {
    "status",
    "next_attempt_at",
    "lease_until",
    "claimed_by",
    "last_attempted_at",
    "retry_count",
    "error_code",
    "error_message",
    "failed_at",
}


async def test_platform_baseline_creates_outbox_retry_state_columns(tmp_path) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path / 'outbox-retry-migration.db'}"
    await run_platform_baseline(url=url)

    session_factory = build_session_factory(url)
    async with session_factory() as session:
        connection = await session.connection()

        def _columns(sync_connection: Any, table_name: str) -> set[str]:
            return {column["name"] for column in inspect(sync_connection).get_columns(table_name)}

        event_columns = await connection.run_sync(_columns, "event_outbox")
        command_columns = await connection.run_sync(_columns, "command_outbox")

    assert set(event_columns) >= _EXPECTED_COLUMNS
    assert set(command_columns) >= _EXPECTED_COLUMNS


async def test_outbox_retry_state_round_trips_on_migrated_schema(tmp_path) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path / 'outbox-retry-roundtrip.db'}"
    await run_platform_baseline(url=url)

    session_factory = build_session_factory(url)
    event_outbox: Any = build_event_delivery_models(MigrationTestModelBase).outbox
    command_outbox: Any = build_command_delivery_models(MigrationTestModelBase).outbox
    async with session_factory() as session:
        session.add(
            event_outbox(
                id="outbox-mig-1",
                event_id="event-mig-1",
                source_service="test_service",
                integration_event_name="SampleIntegrationEvent",
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
                aggregate_id="aggregate-1",
                schema_version=1,
                payload={},
                correlation_id="c",
                causation_id="k",
                status=OutboxStatus.RETRY.value,
                retry_count=2,
                error_code="TRANSPORT_ERROR",
                error_message="TimeoutError: broker timed out",
            )
        )
        session.add(
            command_outbox(
                id="outbox-mig-2",
                command_id="command-mig-2",
                command_name="SampleCommand",
                source_service="test_service",
                target_service="other_service",
                schema_version=1,
                issued_at=datetime(2026, 1, 1, tzinfo=UTC),
                payload={},
                correlation_id="c",
                causation_id="k",
            )
        )
        await session.commit()

    async with session_factory() as session:
        event_row = (
            await session.execute(select(event_outbox).where(event_outbox.id == "outbox-mig-1"))
        ).scalar_one()
        command_row = (
            await session.execute(select(command_outbox).where(command_outbox.id == "outbox-mig-2"))
        ).scalar_one()

    assert event_row.status == OutboxStatus.RETRY.value
    assert event_row.retry_count == 2
    assert event_row.error_code == "TRANSPORT_ERROR"
    assert event_row.error_message == "TimeoutError: broker timed out"
    assert event_row.next_attempt_at is not None
    assert command_row.status == OutboxStatus.PENDING.value
    assert command_row.retry_count == 0
    assert command_row.published_at is None
