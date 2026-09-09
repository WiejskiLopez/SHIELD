"""Mapper domain events to explicitly registered integration events."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.application.context.correlation_id import (
    get_or_create_correlation_id,
)
from shell.platform.application.events import IntegrationEvent
from shell.platform.infrastructure.mapping.integration_mapping_error import (
    IntegrationMappingError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

ENVELOPE_FIELDS: frozenset[str] = frozenset(f.name for f in dataclasses.fields(IntegrationEvent))


class IntegrationEventMapper:
    def __init__(self, integration_events: Mapping[str, type]) -> None:
        self._integration_events = integration_events

    def map(self, domain_event: object) -> object:
        int_cls = self._integration_events.get(type(domain_event).__name__)
        if int_cls is None:
            raise IntegrationMappingError(
                f"Brak zarejestrowanego zdarzenia integracyjnego dla "
                f"{type(domain_event).__name__}"
            )

        kwargs: dict[str, Any] = {
            "event_id": str(domain_event.event_id.value),  # type: ignore[attr-defined]
            "correlation_id": get_or_create_correlation_id(),
            "causation_id": get_causation_id(),
            "occurred_at": domain_event.occurred_at.value,  # type: ignore[attr-defined]
            "aggregate_id": self._aggregate_id(domain_event),
            "schema_version": 1,
        }

        for f in dataclasses.fields(int_cls):
            if f.name in ENVELOPE_FIELDS:
                continue

            raw: Any = getattr(domain_event, f.name)
            kwargs[f.name] = self._to_str(raw)

        return int_cls(**kwargs)

    def _aggregate_id(self, domain_event: object) -> str:
        id_fields = [
            field.name
            for field in dataclasses.fields(domain_event)
            if field.name.endswith("_id") and field.name != "event_id"
        ]
        if len(id_fields) == 1:
            identifier = getattr(domain_event, id_fields[0])
            return str(identifier.value)
        preferred = self._preferred_aggregate_id_field(type(domain_event).__name__, id_fields)
        if preferred is not None:
            identifier = getattr(domain_event, preferred)
            return str(identifier.value)
        raise IntegrationMappingError(
            f"Zdarzenie domenowe {type(domain_event).__name__} musi definiować dokładnie jedno "
            "pole ID agregatu"
        )

    @staticmethod
    def _preferred_aggregate_id_field(event_name: str, id_fields: list[str]) -> str | None:
        """Wybierz ID agregatu gdy event niesie dodatkowe referencje (np. user_id).

        Reguła: prefix nazwy eventu (bez suffixu Created/Changed/...) w snake_case
        musi odpowiadać nazwie pola, np. SessionOpenedEvent -> session_id.
        """
        suffixes = (
            "CreatedEvent",
            "ChangedEvent",
            "DeletedEvent",
            "OpenedEvent",
            "ClosedEvent",
            "RevokedEvent",
            "StartedEvent",
            "CompletedEvent",
            "FailedEvent",
            "FinishedEvent",
            "AbortedEvent",
            "PausedEvent",
            "ResumedEvent",
            "RenamedEvent",
            "ExhaustedEvent",
            "TimedOutEvent",
            "RetriedEvent",
            "TimeoutEvent",
            "Event",
        )
        prefix = event_name
        for suffix in suffixes:
            if event_name.endswith(suffix):
                prefix = event_name[: -len(suffix)]
                break
        snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in prefix).lstrip("_")
        candidate = f"{snake}_id" if snake else ""
        if candidate in id_fields:
            return candidate
        return None

    def _to_str(self, raw: Any) -> str | None:
        if raw is None:
            return None
        return str(getattr(raw, "value", raw))