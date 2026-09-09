"""Szyna zapytań (QueryBus) - rejestruje i dyspozytuje zapytania do handlerów."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shell.platform.application.exceptions.application_contract_error import (
    QueryHandlerNotFoundError,
    QueryHandlerRegistrationError,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class QueryBus:
    """Przesyła zapytania do dynamicznie rozwiązanych handlerów."""

    def __init__(self) -> None:
        self._factories: dict[type[Any], Callable[[], Any]] = {}

    def register(self, query_type: type[Any], factory: Callable[[], Any]) -> None:
        if query_type in self._factories:
            raise QueryHandlerRegistrationError(
                f"Query handler already registered for {query_type.__name__}"
            )
        self._factories[query_type] = factory

    async def dispatch(self, query: Any) -> Any:
        factory = self._factories.get(type(query))
        if factory is None:
            raise QueryHandlerNotFoundError(f"No handler registered for {type(query).__name__}")
        handler = factory()
        return await handler.handle(query)
