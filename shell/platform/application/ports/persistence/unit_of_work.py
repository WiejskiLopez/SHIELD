"""Port jednostki pracy (UnitOfWork) - kontrakt transakcyjności."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from shell.platform.application.contracts.command_contract import CommandContract


class IntegrationEventMapper(Protocol):
    def map(self, domain_event: object) -> object: ...


class UnitOfWork(Protocol):
    def repository(self, repo_type: type[Any]) -> Any: ...

    def stage_events(self, events: Sequence[object]) -> None: ...

    def stage_commands(
        self, commands: Sequence[tuple[CommandContract, object]]
    ) -> None: ...

    async def save(self, repo_type: type, aggregate: object) -> None: ...

    async def save_many(self, aggregates: Sequence[tuple[type, object]]) -> None: ...

    @property
    def events(self) -> Sequence[object]: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None: ...
