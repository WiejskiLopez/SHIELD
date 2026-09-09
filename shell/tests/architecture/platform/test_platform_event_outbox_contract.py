"""Koncept: kontrakt platformowego event outbox.

Reguła: model event outbox musi zawierać pola delivery, kolumny stanu retry
oraz indeksy publikacji i claimowania.

Poprawnie: kod spełnia ten kontrakt i nie zgłasza naruszeń.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import MetaData, Table
from sqlalchemy.orm import DeclarativeBase

from shell.platform.infrastructure.persistence.sql.models.event_delivery import (
    build_event_delivery_models,
)


def test_event_outbox_model_has_delivery_contract() -> None:
    class DeliveryBase(DeclarativeBase):
        metadata = MetaData()

    outbox = cast("Table", build_event_delivery_models(DeliveryBase).outbox.__table__)
    assert {
        "id",
        "event_id",
        "source_service",
        "integration_event_name",
        "occurred_at",
        "aggregate_id",
        "schema_version",
        "payload",
        "correlation_id",
        "causation_id",
        "published_at",
        "status",
        "next_attempt_at",
        "lease_until",
        "claimed_by",
        "last_attempted_at",
        "retry_count",
        "error_code",
        "error_message",
        "failed_at",
    } == set(outbox.columns.keys())
    assert {"uq_event_outbox_event_id"} == {
        constraint.name for constraint in outbox.constraints if constraint.name
    }
    assert {"ix_event_outbox_publish", "ix_event_outbox_status_next_attempt"} == {
        index.name for index in outbox.indexes if index.name
    }
