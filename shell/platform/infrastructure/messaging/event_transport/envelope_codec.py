"""EventEnvelopeCodec — (de)serializacja JSON koperty zdarzenia integracyjnego."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shell.platform.application.ports.transport.event_transport import (
    EventDeliveryEnvelope,
)
from shell.platform.infrastructure.serialization.errors import (
    MissingEnvelopeFieldError,
    SerializationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


class EnvelopeCodec:
    """Koduje kopertę dostawy zdarzenia integracyjnego na bajty JSON i z powrotem.

    Przewód niesie ``contract_type`` (stabilna nazwa kontraktu) oraz ``occurred_at``;
    metadane zdarzenia przechowywane w dedykowanych polach, nie w payload. Kanał
    wynika z typu koperty, więc na przewodzie nie ma ``kind``/``outbox_id``.
    """

    def encode(self, envelope: EventDeliveryEnvelope) -> bytes:
        raw_occurred_at = envelope.occurred_at
        if not isinstance(raw_occurred_at, datetime):
            raise SerializationError(
                f"occurred_at musi być datetime, otrzymano {type(raw_occurred_at).__name__}"
            )
        occurred_at = raw_occurred_at.isoformat()
        document: dict[str, object] = {
            "contract_type": envelope.contract_type,
            "occurred_at": occurred_at,
            "schema_version": envelope.schema_version,
            "payload": envelope.payload,
            "correlation_id": envelope.correlation_id,
            "causation_id": envelope.causation_id,
            "event_id": envelope.event_id,
            "source_service": envelope.source_service,
            "destination_service": envelope.destination_service,
            "aggregate_id": envelope.aggregate_id,
        }
        return json.dumps(document, separators=(",", ":")).encode("utf-8")

    def decode(self, raw: bytes) -> EventDeliveryEnvelope:
        document: Mapping[str, object] = json.loads(raw.decode("utf-8"))
        payload = document.get("payload", {})
        if not isinstance(payload, dict):
            raise SerializationError(f"payload musi być mapowaniem, otrzymano {type(payload).__name__}")
        return EventDeliveryEnvelope(
            contract_type=str(self._required(document, "contract_type")),
            occurred_at=self._parse_occurred_at(str(self._required(document, "occurred_at"))),
            payload=dict(payload),
            correlation_id=str(document.get("correlation_id", "")),
            causation_id=str(document.get("causation_id", "")),
            schema_version=self._parse_schema_version(document.get("schema_version", 1)),
            event_id=str(document["event_id"]) if document.get("event_id") else "",
            source_service=(
                str(document["source_service"]) if document.get("source_service") else ""
            ),
            destination_service=(
                str(document["destination_service"]) if document.get("destination_service") else ""
            ),
            aggregate_id=(str(document["aggregate_id"]) if document.get("aggregate_id") else ""),
        )

    @staticmethod
    def _required(document: Mapping[str, object], field: str) -> object:
        if field not in document:
            raise MissingEnvelopeFieldError(f"koperta brakuje wymaganego pola: {field}")
        return document[field]

    @staticmethod
    def _parse_schema_version(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise SerializationError(f"schema_version musi być int, otrzymano {type(value).__name__}")
        return value

    @staticmethod
    def _parse_occurred_at(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)