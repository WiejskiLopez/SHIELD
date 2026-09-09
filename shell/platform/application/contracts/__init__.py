"""Kontrakty aplikacyjne platformy (CommandContract, ContractCatalog)."""

from __future__ import annotations

from shell.platform.application.contracts.command_contract import CommandContract
from shell.platform.application.contracts.contract_catalog import (
    ContractCatalog,
    ContractEntry,
    build_contract_catalog,
)

__all__ = [
    "CommandContract",
    "ContractCatalog",
    "ContractEntry",
    "build_contract_catalog",
]