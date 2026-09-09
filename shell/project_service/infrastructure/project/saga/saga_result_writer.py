"""Zapis faktów uczestnika do event_outbox (ta sama transakcja co ack inbox)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from shell.platform.application.context.session_scope import get_session_scope
from shell.project_service.application.project.project_provision.integration_events.workspace_provision_failed_integration_event import (
    WorkspaceProvisionFailedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.ports.provision_result_writer import (
    ProvisionResultWriter,
    WorkspaceResultEvent,
)

if TYPE_CHECKING:
    from shell.platform.infrastructure.persistence.sql.models.event_delivery import (
        EventDeliveryModels,
    )


class SqlProvisionResultWriter(ProvisionResultWriter):
    """Uczestnik bez agregatu: fakt trafia wprost do event_outbox serwisu."""

    def __init__(self, event_models: EventDeliveryModels, source_service: str = "project") -> None:
        self._outbox_model = event_models.outbox
        self._source_service = source_service

    def append(self, event: WorkspaceResultEvent) -> None:
        scope = get_session_scope()
        if scope is None or scope.session is None:
            raise RuntimeError("poza UoW nie wolno dopisywać do event_outbox")
        payload: dict[str, object] = {
            "project_id": event.project_id,
            "attempt": event.attempt,
        }
        if isinstance(event, WorkspaceProvisionFailedIntegrationEvent):
            payload["reason"] = event.reason
        scope.session.add(
            self._outbox_model(
                id=str(uuid.uuid4()),
                event_id=event.event_id,
                source_service=self._source_service,
                integration_event_name=type(event).__name__,
                occurred_at=event.occurred_at,
                aggregate_id=event.aggregate_id,
                schema_version=event.schema_version,
                published_at=None,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                payload=payload,
            )
        )
