"""Most wyników kroku provision: fakty z inboxu -> advance sagi (idempotentny)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.application.advance_saga_handler import AdvanceSagaCommand
from saga_orchestration.domain.processed_delivery import DeliveryId
from saga_orchestration.domain.saga_key import SagaKey

from shell.platform.application.event_handlers.event_handler import EventHandler
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provision_failed_integration_event import (
    ScheduleProvisionFailedIntegrationEvent,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provisioned_integration_event import (
    ScheduleProvisionedIntegrationEvent,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_definition import (
    SAGA_TYPE,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_dispatch import (
    PROVISION_STEP,
)

if TYPE_CHECKING:
    from saga_orchestration.application.advance_saga_handler import AdvanceSagaHandler

ProvisionResultEvent = ScheduleProvisionedIntegrationEvent | ScheduleProvisionFailedIntegrationEvent
"""Cykl wynikowy jednego kroku: dokładnie jeden z pary (Union dozwolony dla process)."""


class ProvisionResultBridgeHandler(EventHandler[ProvisionResultEvent]):
    """Subskrypcja EventBus (karmionego przez EventInboxProcessor). Stateless."""

    def __init__(self, advance_handler: AdvanceSagaHandler) -> None:
        self._advance_handler = advance_handler

    async def handle(self, event: ProvisionResultEvent) -> None:
        await self._advance_handler.handle(
            AdvanceSagaCommand(
                key=SagaKey(saga_type=SAGA_TYPE, business_key=event.scheduler_job_id),
                delivery_id=DeliveryId(event.event_id),
                step=PROVISION_STEP,
                attempt=event.attempt,
                succeeded=isinstance(event, ScheduleProvisionedIntegrationEvent),
                is_compensation=False,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
            )
        )
