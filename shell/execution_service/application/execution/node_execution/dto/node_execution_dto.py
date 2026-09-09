from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NodeExecutionDto:
    id: str
    node_type: str
