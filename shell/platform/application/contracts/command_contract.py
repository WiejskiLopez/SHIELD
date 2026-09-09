"""Kontrakt przewodowy komendy — jawna, stabilna tożsamość komendy asynchronicznej."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from shell.platform.application.commands.command import Command


@dataclass(frozen=True, slots=True)
class CommandContract:
    """Stabilna tożsamość przewodowa komendy; niezależna od nazwy klasy w Pythonie."""

    command_name: str
    command_class: type[Command]
    target_service: str
    schema_version: int = 1


def command_contracts_by_class(
    contracts: Mapping[str, CommandContract],
) -> dict[type, CommandContract]:
    """Indeks kontraktów po klasie komendy dla O(1) wyszukiwania przy dyspachingu."""
    return {contract.command_class: contract for contract in contracts.values()}