from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError

if TYPE_CHECKING:
    from saga_orchestration.domain.json_value import JsonValue


@dataclass(frozen=True, slots=True)
class OutboxCommandRow(ValueObject):
    """Kontrakt transportowy (envelope) — budowany jawnie, nigdy z payloadu."""

    command_id: str
    source_service: str
    destination_service: str
    contract_type: str
    schema_version: int
    aggregate_id: str
    payload: dict[str, JsonValue]
    correlation_id: str
    causation_id: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "command_id",
            "source_service",
            "destination_service",
            "contract_type",
            "aggregate_id",
            "correlation_id",
        ):
            if not getattr(self, field_name):
                raise SagaDomainError(f"envelope.{field_name} jest wymagane")
        if self.schema_version < 1:
            raise SagaDomainError("envelope.schema_version >= 1")


class CommandOutboxWriter(Protocol):
    """Port implementowany przez SERWIS (mapuje wiersz na jego command_outbox)."""

    def append(self, row: OutboxCommandRow) -> None:
        """Dopisz do bieżącej sesji UoW. Bez commit — commit należy do UoW."""
