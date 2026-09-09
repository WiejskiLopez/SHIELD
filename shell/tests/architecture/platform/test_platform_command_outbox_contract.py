"""Koncept: kontrakt platformowego command outbox.

Reguła: model command outbox musi zawierać pola delivery, indeks i unikalność.

Poprawnie: kod spełnia ten kontrakt i nie zgłasza naruszeń.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import MetaData, Table
from sqlalchemy.orm import DeclarativeBase

from shell.platform.infrastructure.persistence.sql.models.command_delivery import (
    build_command_delivery_models,
)


def test_command_outbox_model_has_delivery_contract() -> None:
    class DeliveryBase(DeclarativeBase):
        metadata = MetaData()

    outbox = cast("Table", build_command_delivery_models(DeliveryBase).outbox.__table__)
    assert {
        "id",
        "command_id",
        "command_name",
        "source_service",
        "target_service",
        "schema_version",
        "issued_at",
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
    assert {"uq_command_outbox_source_cmd"} == {
        constraint.name for constraint in outbox.constraints if constraint.name
    }
    assert {"ix_command_outbox_publish", "ix_command_outbox_status_next_attempt"} == {
        index.name for index in outbox.indexes if index.name
    }
