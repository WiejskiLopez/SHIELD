"""SQLite integration tests for EventOutboxRelay (producer-side bridge)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from shell.platform.domain.value_objects.outbox_status import OutboxStatus
from shell.platform.infrastructure.messaging.delivery.outbox_relay_base import (
    ENVELOPE_BUILD_ERROR,
    TRANSPORT_ERROR,
    OutboxRelayAbortedError,
)
from shell.platform.infrastructure.messaging.event import EventOutboxRelay
from shell.platform.infrastructure.persistence.sql import build_session_factory
from shell.tests.platform.integration.platform_delivery_models import (
    EVENT_DELIVERY_MODELS,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from shell.platform.application.ports.transport.event_transport import (
        EventDeliveryEnvelope,
    )

_OUTBOX_MODEL: Any = EVENT_DELIVERY_MODELS.outbox

_BASE_ROW: dict[str, Any] = {
    "source_service": "test_service",
    "integration_event_name": "SampleIntegrationEvent",
    "aggregate_id": "aggregate-1",
    "schema_version": 1,
    "payload": {"sample_field": "sample-value"},
    "correlation_id": "correlation-1",
    "causation_id": "causation-1",
}


async def _seed_rows(
    session_factory: async_sessionmaker,
    specs: list[dict[str, Any]],
) -> None:
    async with session_factory() as session:
        for index, spec in enumerate(specs):
            row = dict(_BASE_ROW)
            row.update(spec)
            row.setdefault("id", f"outbox-{index}")
            row.setdefault("event_id", f"event-{index}")
            row.setdefault("occurred_at", datetime(2026, 1, 1, tzinfo=UTC))
            session.add(_OUTBOX_MODEL(**row))
        await session.commit()


async def _isolated_factory(tmp_path, db_name: str) -> async_sessionmaker:
    url = f"sqlite+aiosqlite:///{tmp_path / db_name}"
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(_OUTBOX_MODEL.metadata.create_all)
    await engine.dispose()
    return build_session_factory(url)


async def _rows(session_factory: async_sessionmaker) -> list[Any]:
    async with session_factory() as session:
        return (
            (await session.execute(select(_OUTBOX_MODEL).order_by(_OUTBOX_MODEL.id)))
            .scalars()
            .all()
        )


class RecordingTransport:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.delivered: list[EventDeliveryEnvelope] = []

    async def deliver(self, envelope: EventDeliveryEnvelope) -> None:
        if self.fail:
            raise RuntimeError("broker unavailable")
        self.delivered.append(envelope)


class PoisonTransport(RecordingTransport):
    """Fails only for the poison event id — every other row delivers."""

    def __init__(self, poison_event_id: str) -> None:
        super().__init__()
        self.poison_event_id = poison_event_id

    async def deliver(self, envelope: EventDeliveryEnvelope) -> None:
        if envelope.event_id == self.poison_event_id:
            raise RuntimeError("poison envelope cannot be published")
        self.delivered.append(envelope)


class FlakyTimeoutTransport(RecordingTransport):
    """Fails the first delivery with a timeout, then succeeds (retry test)."""

    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    async def deliver(self, envelope: EventDeliveryEnvelope) -> None:
        self.attempts += 1
        if self.attempts == 1:
            raise TimeoutError("broker timed out")
        self.delivered.append(envelope)


class AcceptedThenTimeoutTransport(RecordingTransport):
    """Records broker acceptance before the producer observes a timeout."""

    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    async def deliver(self, envelope: EventDeliveryEnvelope) -> None:
        self.attempts += 1
        self.delivered.append(envelope)
        if self.attempts == 1:
            raise TimeoutError("broker response was lost")


class UnroutableThenRoutableTransport(RecordingTransport):
    """Fails with an unroutable publish error until a binding is added."""

    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    async def deliver(self, envelope: EventDeliveryEnvelope) -> None:
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("NO_ROUTE: unroutable message (binding missing)")
        self.delivered.append(envelope)


class BrokenBrokerTransport(RecordingTransport):
    """Simulates a down broker: every publish fails at connect time."""

    async def deliver(self, envelope: EventDeliveryEnvelope) -> None:
        raise ConnectionError("broker unreachable")


class TestEventOutboxRelay:
    async def test_delivers_pending_and_marks_sent(
        self,
        session_factory: async_sessionmaker,
    ) -> None:
        await _seed_rows(session_factory, [{"id": "outbox-1", "event_id": "event-1"}])

        transport = RecordingTransport()
        relay = EventOutboxRelay(session_factory, EVENT_DELIVERY_MODELS, transport)
        result = await relay.run_once()

        assert result.claimed_count == 1
        assert result.processed_count == 1
        assert result.retried_count == 0
        assert result.dead_lettered_count == 0
        assert result.failed_count == 0
        assert len(transport.delivered) == 1
        delivered_event = transport.delivered[0]
        assert delivered_event.contract_type == "SampleIntegrationEvent"
        assert delivered_event.event_id == "event-1"
        assert delivered_event.schema_version == 1
        assert delivered_event.payload == {"sample_field": "sample-value"}

        rows = await _rows(session_factory)
        assert len(rows) == 1
        assert rows[0].status == OutboxStatus.SENT.value
        assert rows[0].published_at is not None
        assert rows[0].retry_count == 0

    async def test_poison_row_does_not_block_healthy_rows(
        self,
        tmp_path,
    ) -> None:
        """Regression test: one poison envelope must not block the batch behind it."""
        isolated = await _isolated_factory(tmp_path, "relay-poison.db")
        await _seed_rows(
            isolated,
            [
                {
                    "id": "outbox-poison",
                    "event_id": "event-poison",
                    "occurred_at": datetime(2026, 1, 1, tzinfo=UTC),
                },
                {
                    "id": "outbox-good",
                    "event_id": "event-good",
                    "occurred_at": datetime(2026, 1, 2, tzinfo=UTC),
                },
            ],
        )

        transport = PoisonTransport(poison_event_id="event-poison")
        relay = EventOutboxRelay(isolated, EVENT_DELIVERY_MODELS, transport)
        result = await relay.run_once()

        assert result.claimed_count == 2
        assert result.processed_count == 1
        assert result.retried_count == 1
        assert [envelope.event_id for envelope in transport.delivered] == ["event-good"]

        rows = {row.id: row for row in await _rows(isolated)}
        assert rows["outbox-good"].status == OutboxStatus.SENT.value
        assert rows["outbox-good"].published_at is not None
        assert rows["outbox-poison"].status == OutboxStatus.RETRY.value
        assert rows["outbox-poison"].published_at is None
        assert rows["outbox-poison"].retry_count == 1
        assert rows["outbox-poison"].error_code == TRANSPORT_ERROR

    async def test_row_dead_letters_after_max_retries(self, tmp_path) -> None:
        isolated = await _isolated_factory(tmp_path, "relay-dlq.db")
        await _seed_rows(isolated, [{"id": "outbox-1", "event_id": "event-1"}])

        relay = EventOutboxRelay(
            isolated,
            EVENT_DELIVERY_MODELS,
            RecordingTransport(fail=True),
            max_retries=2,
            retry_backoff_seconds=0,
        )

        first = await relay.run_once()
        assert first.retried_count == 1
        rows = await _rows(isolated)
        assert rows[0].status == OutboxStatus.RETRY.value
        assert rows[0].retry_count == 1

        second = await relay.run_once()
        assert second.dead_lettered_count == 1
        rows = await _rows(isolated)
        assert rows[0].status == OutboxStatus.DEAD_LETTER.value
        assert rows[0].retry_count == 2
        assert rows[0].published_at is None
        assert rows[0].failed_at is not None
        assert rows[0].error_code == TRANSPORT_ERROR

        third = await relay.run_once()
        assert third.claimed_count == 0
        assert third.processed_count == 0

    async def test_retry_schedules_next_attempt_with_backoff(self, tmp_path) -> None:
        isolated = await _isolated_factory(tmp_path, "relay-backoff.db")
        await _seed_rows(isolated, [{"id": "outbox-1", "event_id": "event-1"}])

        relay = EventOutboxRelay(isolated, EVENT_DELIVERY_MODELS, RecordingTransport(fail=True))
        result = await relay.run_once()

        assert result.retried_count == 1
        rows = await _rows(isolated)
        assert rows[0].last_attempted_at is not None
        assert rows[0].next_attempt_at > rows[0].last_attempted_at
        assert rows[0].next_attempt_at - rows[0].last_attempted_at >= timedelta(seconds=30)

        skipped = await relay.run_once()
        assert skipped.claimed_count == 0

    async def test_broker_outage_aborts_round_without_burning_retries(
        self,
        tmp_path,
    ) -> None:
        isolated = await _isolated_factory(tmp_path, "relay-outage.db")
        await _seed_rows(
            isolated,
            [
                {"id": "outbox-1", "event_id": "event-1"},
                {"id": "outbox-2", "event_id": "event-2"},
            ],
        )

        relay = EventOutboxRelay(isolated, EVENT_DELIVERY_MODELS, BrokenBrokerTransport())
        try:
            await relay.run_once()
        except OutboxRelayAbortedError:
            pass
        else:
            raise AssertionError("expected OutboxRelayAbortedError on broker outage")

        rows = {row.id: row for row in await _rows(isolated)}
        for row in rows.values():
            assert row.status == OutboxStatus.PENDING.value
            assert row.retry_count == 0
            assert row.published_at is None

    async def test_consecutive_failure_breaker_trips_and_raises(self, tmp_path) -> None:
        isolated = await _isolated_factory(tmp_path, "relay-breaker.db")
        await _seed_rows(
            isolated,
            [{"id": f"outbox-{index}", "event_id": f"event-{index}"} for index in range(3)],
        )

        relay = EventOutboxRelay(
            isolated,
            EVENT_DELIVERY_MODELS,
            RecordingTransport(fail=True),
            consecutive_failure_limit=2,
        )
        try:
            await relay.run_once()
        except OutboxRelayAbortedError as exc:
            assert "breaker" in str(exc)
        else:
            raise AssertionError("expected OutboxRelayAbortedError from breaker trip")

        rows = {row.id: row for row in await _rows(isolated)}
        assert rows["outbox-0"].status == OutboxStatus.RETRY.value
        assert rows["outbox-1"].status == OutboxStatus.RETRY.value
        assert rows["outbox-2"].status == OutboxStatus.PENDING.value
        assert rows["outbox-2"].retry_count == 0

    async def test_envelope_build_failure_dead_letters_immediately(
        self,
        tmp_path,
    ) -> None:
        isolated = await _isolated_factory(tmp_path, "relay-mapping.db")
        await _seed_rows(
            isolated,
            [
                {"id": "outbox-broken", "event_id": "event-broken"},
                {"id": "outbox-good", "event_id": "event-good"},
            ],
        )

        relay = _BrokenEnvelopeRelay(isolated, EVENT_DELIVERY_MODELS, RecordingTransport())
        result = await relay.run_once()

        assert result.processed_count == 1
        assert result.dead_lettered_count == 1
        rows = {row.id: row for row in await _rows(isolated)}
        assert rows["outbox-good"].status == OutboxStatus.SENT.value
        assert rows["outbox-broken"].status == OutboxStatus.DEAD_LETTER.value
        assert rows["outbox-broken"].retry_count == 1
        assert rows["outbox-broken"].error_code == ENVELOPE_BUILD_ERROR

    async def test_transport_failure_records_retry_without_publishing(
        self,
        tmp_path,
    ) -> None:
        isolated = await _isolated_factory(tmp_path, "relay-fail.db")
        await _seed_rows(isolated, [{"id": "outbox-1", "event_id": "event-1"}])

        relay = EventOutboxRelay(
            isolated,
            EVENT_DELIVERY_MODELS,
            RecordingTransport(fail=True),
        )
        result = await relay.run_once()

        assert result.retried_count == 1
        assert result.processed_count == 0
        rows = await _rows(isolated)
        assert len(rows) == 1
        assert rows[0].published_at is None
        assert rows[0].status == OutboxStatus.RETRY.value
        assert rows[0].retry_count == 1

    async def test_timeout_is_retried_and_then_delivered(
        self,
        tmp_path,
    ) -> None:
        """A broker timeout must not lose the outbox row or mark it published."""
        isolated = await _isolated_factory(tmp_path, "relay-timeout.db")

        await _seed_rows(isolated, [{"id": "outbox-1", "event_id": "event-1"}])

        transport = FlakyTimeoutTransport()
        relay = EventOutboxRelay(
            isolated,
            EVENT_DELIVERY_MODELS,
            transport,
            retry_backoff_seconds=0,
        )

        first = await relay.run_once()
        assert first.retried_count == 1
        rows = await _rows(isolated)
        assert len(rows) == 1
        assert rows[0].published_at is None
        assert rows[0].status == OutboxStatus.RETRY.value

        second = await relay.run_once()
        assert second.processed_count == 1
        assert len(transport.delivered) == 1
        rows = await _rows(isolated)
        assert rows[0].published_at is not None
        assert rows[0].status == OutboxStatus.SENT.value

    async def test_ambiguous_transport_result_keeps_at_least_once_delivery(
        self,
        tmp_path,
    ) -> None:
        isolated = await _isolated_factory(tmp_path, "relay-ambiguous.db")

        await _seed_rows(isolated, [{"id": "outbox-1", "event_id": "event-1"}])

        transport = AcceptedThenTimeoutTransport()
        relay = EventOutboxRelay(
            isolated,
            EVENT_DELIVERY_MODELS,
            transport,
            retry_backoff_seconds=0,
        )

        first = await relay.run_once()
        assert first.retried_count == 1
        rows = await _rows(isolated)
        assert rows[0].published_at is None

        assert len(transport.delivered) == 1
        second = await relay.run_once()
        assert second.processed_count == 1
        assert len(transport.delivered) == 2

        rows = await _rows(isolated)
        assert rows[0].published_at is not None
        assert rows[0].status == OutboxStatus.SENT.value

    async def test_unroutable_error_is_retried_after_binding_added(
        self,
        tmp_path,
    ) -> None:
        """An unroutable publish (no binding) must not mark the record,
        and the relay must deliver it once the binding exists (retry)."""
        isolated = await _isolated_factory(tmp_path, "relay-unroutable.db")

        await _seed_rows(isolated, [{"id": "outbox-1", "event_id": "event-1"}])

        transport = UnroutableThenRoutableTransport()
        relay = EventOutboxRelay(
            isolated,
            EVENT_DELIVERY_MODELS,
            transport,
            retry_backoff_seconds=0,
        )

        first = await relay.run_once()
        assert first.retried_count == 1
        rows = await _rows(isolated)
        assert len(rows) == 1
        assert rows[0].published_at is None
        assert rows[0].status == OutboxStatus.RETRY.value

        second = await relay.run_once()
        assert second.processed_count == 1
        assert len(transport.delivered) == 1

        rows = await _rows(isolated)
        assert rows[0].published_at is not None
        assert rows[0].status == OutboxStatus.SENT.value


class _BrokenEnvelopeRelay(EventOutboxRelay):
    """Fails envelope mapping for the broken row — deterministic poison mapping."""

    def _to_envelope(self, row: object) -> EventDeliveryEnvelope:
        if getattr(row, "event_id", None) == "event-broken":
            raise RuntimeError("no mapping for legacy payload")
        return super()._to_envelope(row)
