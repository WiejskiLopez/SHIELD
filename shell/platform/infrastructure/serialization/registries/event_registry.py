"""Rejestr zdarzeń (budowanie, auto-discovery, mapa Domain→Integration)."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import TYPE_CHECKING

from shell.platform.application.events import IntegrationEvent
from shell.platform.infrastructure.serialization.registries.type_registry import build_type_registry

if TYPE_CHECKING:
    from collections.abc import Iterable

    from shell.platform.application.contracts.contract_catalog import ContractCatalog


def build_event_registry(event_types: Iterable[type]) -> dict[str, type]:
    """Build a registry from event types supplied by the composition root."""
    return build_type_registry(event_types)


def build_domain_event_mapper_registry(registry: dict[str, type]) -> dict[str, type]:
    """Build the explicit DomainEvent-to-IntegrationEvent mapping for a BC."""
    return {
        integration_name.removesuffix("IntegrationEvent") + "Event": integration_type
        for integration_name, integration_type in registry.items()
    }


def build_bounded_context_event_registry(
    *,
    package: str,
    catalog: ContractCatalog,
    consumed: tuple[type, ...] = (),
) -> dict[str, type]:
    """Build a bounded-context event registry from discovery plus consumed contracts."""
    owned = discover_event_types(package, IntegrationEvent)
    registry = build_event_registry((*owned, *consumed))
    catalog.assert_covers(registry)
    return registry


def discover_event_types(package_name: str, base_type: type) -> tuple[type, ...]:
    """Discover event classes below a bounded context application package."""
    package = importlib.import_module(package_name)
    package_paths = getattr(package, "__path__", ())
    event_types: list[type] = []
    for package_path in package_paths:
        root = Path(package_path)
        for module_path in root.rglob("integration_events/*.py"):
            if module_path.name == "__init__.py":
                continue
            relative_module = module_path.relative_to(root).with_suffix("")
            module_name = ".".join(relative_module.parts)
            module = importlib.import_module(f"{package_name}.{module_name}")
            for candidate in vars(module).values():
                if (
                    inspect.isclass(candidate)
                    and candidate is not base_type
                    and issubclass(candidate, base_type)
                    and candidate.__module__ == module.__name__
                ):
                    event_types.append(candidate)
    return tuple(event_types)
