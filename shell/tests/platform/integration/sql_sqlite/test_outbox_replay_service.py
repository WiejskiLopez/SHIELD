"""SQLite integration tests for OutboxReplayService (administrative DLQ replay)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from shell.platform.domain.value_objects.outbox_status import OutboxStatus
from shell.platform.infrastructure.messaging.delivery.outbox_replay_service import (
    OutboxReplayService,
)
from shell.platform.infrastructure.persistence.sql import build_session_factory
from shell.tests.platform.integration.platform_delivery_models import (
    EVENT_DELIVERY_MODELS,
)

_OUTBOX_MODEL: Any = EVENT_DELIVERY_MODELS.outbox


async def _isolated_factory(tmp_path) -> Any:
    url = f"sqlite+aiosqlite:///{tmp_path / 'outbox-replay.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(_OUTBOX_MODEL.metadata.create_all)
    await engine.dispose()
    return build_session_factory(url)


async def _seed_row(session_factory, **overrides: Any) -> None:
    row = {
        "id": "outbox-1",
        "event_id": "event-1",
        "source_service": "test_service",
        "integration_event_name": "SampleIntegrationEvent",
        "occurred_at": datetime(2026, 1, 1, tzinfo=UTC),
        "aggregate_id": "aggregate-1",
        "schema_version": 1,
        "payload": {},
        "correlation_id": "c",
        "causation_id": "k",
        "status": OutboxStatus.DEAD_LETTER.value,
        "retry_count": 3,
        "failed_at": datetime(2026, 2, 1, tzinfo=UTC),
        "error_code": "TRANSPORT_ERROR",
        "error_message": "RuntimeError: broker unavailable",
    }
    row.update(overrides)
    async with session_factory() as session:
        session.add(_OUTBOX_MODEL(**row))
        await session.commit()


async def _get(session_factory, row_id: str) -> Any:
    async with session_factory() as session:
        return (
            await session.execute(select(_OUTBOX_MODEL).where(_OUTBOX_MODEL.id == row_id))
        ).scalar_one()


class TestOutboxReplayService:
    async def test_replay_by_id_resets_dead_letter_to_pending(self, tmp_path) -> None:
        session_factory = await _isolated_factory(tmp_path)
        await _seed_row(session_factory)
        service = OutboxReplayService(session_factory, _OUTBOX_MODEL)

        assert await service.replay_by_id("outbox-1", operator="ops", reason="broker fixed")

        row = await _get(session_factory, "outbox-1")
        assert row.status == OutboxStatus.PENDING.value
        assert row.published_at is None
        assert row.retry_count == 0
        assert row.failed_at is None
        assert row.error_code is None
        assert row.error_message is None
        assert row.claimed_by is None
        assert row.lease_until is None

    async def test_replay_by_id_skips_live_processing_lease(self, tmp_path) -> None:
        session_factory = await _isolated_factory(tmp_path)
        await _seed_row(
            session_factory,
            status=OutboxStatus.PROCESSING.value,
            claimed_by="relay-1",
            lease_until=datetime(2036, 1, 1, tzinfo=UTC),
            failed_at=None,
        )
        service = OutboxReplayService(session_factory, _OUTBOX_MODEL)

        assert not await service.replay_by_id("outbox-1", operator="ops", reason="x")

        row = await _get(session_factory, "outbox-1")
        assert row.status == OutboxStatus.PROCESSING.value

    async def test_replay_dead_lettered_batch(self, tmp_path) -> None:
        session_factory = await _isolated_factory(tmp_path)
        await _seed_row(session_factory, id="outbox-1", event_id="event-1")
        await _seed_row(session_factory, id="outbox-2", event_id="event-2")
        service = OutboxReplayService(session_factory, _OUTBOX_MODEL)

        assert await service.replay_dead_lettered(operator="ops", reason="x") == 2

        for row_id in ("outbox-1", "outbox-2"):
            row = await _get(session_factory, row_id)
            assert row.status == OutboxStatus.PENDING.value
            assert row.retry_count == 0
