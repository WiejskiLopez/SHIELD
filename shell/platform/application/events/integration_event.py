"""Zdarzenie integracyjne (IntegrationEvent) — kontrakt między BC.

Wszystkie zdarzenia integracyjne w systemie dziedziczą po tej klasie bazowej,
która definiuje standardowe pola koperty w tym kontekst śledzenia.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class IntegrationEvent:
    event_id: str
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    aggregate_id: str
    schema_version: int