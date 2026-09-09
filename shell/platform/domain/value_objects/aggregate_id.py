"""Identyfikator agregatu (AggregateId).

Identyfikator agregatu używany w zdarzeniach, dziedziczy po EntityId.
"""

from __future__ import annotations

from dataclasses import dataclass

from shell.platform.domain.base.entity_id import EntityId


@dataclass(frozen=True, slots=True)
class AggregateId(EntityId):
    value: str