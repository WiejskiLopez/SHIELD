"""Most wyniku kompensaty: fakt zwolnienia -> advance sagi (idempotentny)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.application.advance_saga_handler import AdvanceSagaCommand
from saga_orchestration.domain.processed_delivery import DeliveryId
from saga_orchestration.domain.saga_key import SagaKey

from shell.platform.application.event_handlers.event_handler import EventHandler
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_released_integration_event import (
    ScheduleReleasedIntegrationEvent,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_definition import (
    SAGA_TYPE,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_dispatch import (
    RELEASE_STEP,
)

if TYPE_CHECKING:
    from saga_orchestration.application.advance_saga_handler import AdvanceSagaHandler


class ReleaseResultBridgeHandler(EventHandler[ScheduleReleasedIntegrationEvent]):
    """Subskrypcja EventBus (karmionego przez EventInboxProcessor). Stateless."""

    def __init__(self, advance_handler: AdvanceSagaHandler) -> None:
        self._advance_handler = advance_handler

    async def handle(self, event: ScheduleReleasedIntegrationEvent) -> None:
        await self._advance_handler.handle(
            AdvanceSagaCommand(
                key=SagaKey(saga_type=SAGA_TYPE, business_key=event.scheduler_job_id),
                delivery_id=DeliveryId(event.event_id),
                step=RELEASE_STEP,
                attempt=event.attempt,
                succeeded=True,
                is_compensation=True,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
            )
        )
