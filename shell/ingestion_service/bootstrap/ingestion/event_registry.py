"""Ingestion bounded context event registry."""

from __future__ import annotations

from shell.ingestion_service.bootstrap.ingestion.contract_catalog import INGESTION_CONTRACT_CATALOG
from shell.platform.infrastructure.serialization.registries.event_registry import (
    build_bounded_context_event_registry,
)


def build_ingestion_event_registry() -> dict[str, type]:
    """Build the event registry owned by the Ingestion bounded context."""
    return build_bounded_context_event_registry(
        package="shell.ingestion_service.application.ingestion",
        catalog=INGESTION_CONTRACT_CATALOG,
    )
