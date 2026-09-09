"""CommandOutboxRelay — czyta oczekujące wiersze ``command_outbox`` i publikuje przez transport komend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast

from shell.platform.application.ports.transport.command_transport import (
    CommandDeliveryEnvelope,
)
from shell.platform.infrastructure.messaging.delivery.outbox_relay_base import (
    OutboxRelayBase,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from shell.platform.application.ports.transport.command_transport import (
        CommandDeliveryTransport,
    )
    from shell.platform.infrastructure.persistence.sql.models.command_delivery import (
        CommandDeliveryModels,
    )


class CommandOutboxRow(Protocol):
    command_id: str
    command_name: str
    source_service: str
    target_service: str
    schema_version: int
    issued_at: datetime
    payload: dict[str, object]
    correlation_id: str
    causation_id: str
    published_at: datetime | None


class CommandOutboxRelay(OutboxRelayBase):
    """Publikuje oczekujące wiersze outbox komend i oznacza je jako opublikowane przy sukcesie."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        models: CommandDeliveryModels,
        transport: CommandDeliveryTransport,
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
        return self._models.outbox.issued_at

    def _to_envelope(self, row: object) -> CommandDeliveryEnvelope:
        command_row = cast("CommandOutboxRow", row)
        return CommandDeliveryEnvelope(
            command_id=command_row.command_id,
            contract_type=command_row.command_name,
            source_service=command_row.source_service,
            destination_service=command_row.target_service,
            issued_at=command_row.issued_at,
            payload=command_row.payload,
            correlation_id=command_row.correlation_id,
            causation_id=command_row.causation_id,
            schema_version=command_row.schema_version,
        )