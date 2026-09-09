"""Unit tests for the event envelope codec (strict wire validation)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from shell.platform.application.ports.transport.event_transport import (
    EventDeliveryEnvelope,
)
from shell.platform.infrastructure.messaging.event_transport.envelope_codec import (
    EnvelopeCodec,
)
from shell.platform.infrastructure.serialization.errors import (
    MissingEnvelopeFieldError,
    SerializationError,
)


def _envelope(**overrides: object) -> EventDeliveryEnvelope:
    fields: dict[str, object] = {
        "event_id": "event-1",
        "contract_type": "SampleIntegrationEvent",
        "occurred_at": datetime(2026, 1, 1, tzinfo=UTC),
        "aggregate_id": "aggregate-1",
        "schema_version": 1,
        "source_service": "test_service",
        "destination_service": "*",
        "correlation_id": "corr",
        "causation_id": "cause",
        "payload": {"field": "value"},
    }
    fields.update(overrides)
    return EventDeliveryEnvelope(**fields)  # type: ignore[arg-type]


def _wire(**overrides: object) -> bytes:
    document: dict[str, object] = {
        "contract_type": "SampleIntegrationEvent",
        "occurred_at": "2026-01-01T00:00:00+00:00",
        "schema_version": 1,
        "payload": {},
        "correlation_id": "",
        "causation_id": "",
        "event_id": "event-1",
        "source_service": "test_service",
        "destination_service": "*",
        "aggregate_id": "aggregate-1",
    }
    document.update(overrides)
    return json.dumps(document).encode("utf-8")


class TestEnvelopeCodec:
    def test_round_trip_preserves_envelope(self) -> None:
        codec = EnvelopeCodec()
        decoded = codec.decode(codec.encode(_envelope()))

        assert decoded.contract_type == "SampleIntegrationEvent"
        assert decoded.occurred_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert decoded.schema_version == 1
        assert decoded.payload == {"field": "value"}

    def test_encode_rejects_non_datetime_occurred_at(self) -> None:
        codec = EnvelopeCodec()

        with pytest.raises(SerializationError, match="occurred_at must be datetime"):
            codec.encode(_envelope(occurred_at="2026-01-01"))  # type: ignore[arg-type]

    def test_decode_missing_contract_type(self) -> None:
        document = json.loads(_wire().decode("utf-8"))
        del document["contract_type"]

        with pytest.raises(MissingEnvelopeFieldError, match="contract_type"):
            EnvelopeCodec().decode(json.dumps(document).encode("utf-8"))

    def test_decode_missing_occurred_at(self) -> None:
        document = json.loads(_wire().decode("utf-8"))
        del document["occurred_at"]

        with pytest.raises(MissingEnvelopeFieldError, match="occurred_at"):
            EnvelopeCodec().decode(json.dumps(document).encode("utf-8"))

    @pytest.mark.parametrize("bad_version", ["1", 1.0, True, None])
    def test_decode_rejects_non_int_schema_version(self, bad_version: object) -> None:
        with pytest.raises(SerializationError, match="schema_version must be int"):
            EnvelopeCodec().decode(_wire(schema_version=bad_version))

    def test_decode_rejects_non_mapping_payload(self) -> None:
        with pytest.raises(SerializationError, match="payload must be a mapping"):
            EnvelopeCodec().decode(_wire(payload=["not", "a", "mapping"]))

    def test_decode_rejects_malformed_occurred_at(self) -> None:
        with pytest.raises(ValueError):
            EnvelopeCodec().decode(_wire(occurred_at="not-a-datetime"))
