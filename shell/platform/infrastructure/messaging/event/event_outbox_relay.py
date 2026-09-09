"""EventOutboxRelay — czyta oczekujące wiersze ``event_outbox`` i publikuje przez transport zdarzeń."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast

from shell.platform.application.ports.transport.event_transport import (
    EventDeliveryEnvelope,
)
from shell.platform.infrastructure.messaging.delivery.outbox_relay_base import (
    OutboxRelayBase,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.platform.application.ports.transport.event_transport import (
        IntegrationEventDeliveryTransport,
    )
    from shell.platform.infrastructure.persistence.sql.models.event_delivery import (
        EventDeliveryModels,
    )


class EventOutboxRow(Protocol):
    event_id: str
    integration_event_name: str
    occurred_at: datetime
    source_service: str
    aggregate_id: str
    schema_version: int
    payload: dict[str, object]
    correlation_id: str
    causation_id: str
    published_at: datetime | None


class EventOutboxRelay(OutboxRelayBase):
    """Publikuje oczekujące wiersze outbox zdarzeń i oznacza je jako opublikowane przy sukcesie."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        models: EventDeliveryModels,
        transport: IntegrationEventDeliveryTransport,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_backoff_seconds: int = 30,
        max_retry_backoff_seconds: int = 3600,
        retry_jitter_seconds: float = 0.0,
        lease_duration_seconds: int = 60,
        consecutive_failure_limit: int = 20,
        worker_id: str | None = None,
    ) -> None:
        super().__init__(
            session_factory,
            transport,
            batch_size,
            max_retries,
            retry_backoff_seconds,
            max_retry_backoff_seconds,
            retry_jitter_seconds,
            lease_duration_seconds,
            consecutive_failure_limit,
            worker_id,
        )
        self._models = models

    @property
    def outbox_model(self) -> type[Any]:
        return self._models.outbox

    @property
    def order_column(self) -> Any:
        return self._models.outbox.occurred_at

    def _to_envelope(self, row: object) -> EventDeliveryEnvelope:
        event_row = cast("EventOutboxRow", row)
        return EventDeliveryEnvelope(
            event_id=event_row.event_id,
            contract_type=event_row.integration_event_name,
            occurred_at=event_row.occurred_at,
            aggregate_id=event_row.aggregate_id,
            schema_version=event_row.schema_version,
            source_service=event_row.source_service,
            destination_service="*",
            correlation_id=event_row.correlation_id,
            causation_id=event_row.causation_id,
            payload=event_row.payload,
        )