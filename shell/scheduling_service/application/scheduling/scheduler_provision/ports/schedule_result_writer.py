from __future__ import annotations

from typing import Protocol

from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provision_failed_integration_event import (
    ScheduleProvisionFailedIntegrationEvent,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_provisioned_integration_event import (
    ScheduleProvisionedIntegrationEvent,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.integration_events.schedule_released_integration_event import (
    ScheduleReleasedIntegrationEvent,
)

ScheduleResultEvent = (
    ScheduleProvisionedIntegrationEvent
    | ScheduleProvisionFailedIntegrationEvent
    | ScheduleReleasedIntegrationEvent
)
"""Wynik uczestnika sagi: dokładnie jeden z trzech faktów (cykl wynikowy kroku)."""


class ScheduleResultWriter(Protocol):
    """Port zapisu faktu uczestnika do event_outbox — ta sama transakcja co ack."""

    def append(self, event: ScheduleResultEvent) -> None:
        """Dopisz wiersz event_outbox na bieżącej sesji UoW. Bez commit."""
