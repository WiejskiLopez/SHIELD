from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def _qualified_name(item: type) -> str:
    return f"{item.__module__}.{item.__qualname__}"


def build_type_registry(types: Iterable[type]) -> dict[str, type]:
    """Build a deserialization registry keyed by class name.

    The key stays the plain class name because deserializers resolve types
    from the wire ``contract_type`` field, which carries no owner or version.
    A same-name collision of two different classes is therefore a composition
    error: the message names both modules so the conflicting registrations
    can be told apart (typically an owned type shadowing a consumed
    cross-BC contract copy).
    """
    registry: dict[str, type] = {}
    for item in types:
        name = item.__name__
        existing = registry.get(name)
        if existing is not None and existing is not item:
            raise ValueError(
                f"Duplicate registry key: {name} "
                f"({_qualified_name(existing)} vs {_qualified_name(item)})"
            )
        registry[name] = item
    return registry
