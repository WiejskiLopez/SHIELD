from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NodeDefinitionDto:
    id: str
    node_type: str
    node_position: int
    max_step: int | None = None
