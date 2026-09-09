"""Shared transactional lifecycle for bounded-context InMemory unit of works."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, TypeVar

from shell.platform.application.ports.persistence.unit_of_work import UnitOfWork
from shell.platform.domain.events import DomainEvent

if TYPE_CHECKING:
    from collections.abc import Sequence

    from shell.platform.application.contracts.command_contract import CommandContract
TRepository = TypeVar("TRepository")


class InMemoryUnitOfWorkBase(UnitOfWork):
    """Buffer repository writes until commit and restore them on failure."""

    def __init__(self) -> None:
        self._committed = False
        self._staged_events: list[DomainEvent] = []
        self._committed_events: list[object] = []
        self._staged_commands: list[tuple[CommandContract, object]] = []
        self._committed_commands: list[tuple[CommandContract, object]] = []
        self._pending_saves: list[tuple[type, object]] = []

    def stage_events(self, events: Sequence[object]) -> None:
        invalid = [event for event in events if not isinstance(event, DomainEvent)]
        if invalid:
            raise TypeError("InMemoryUnitOfWork stages DomainEvent instances only")
        self._staged_events.extend(events)

    def stage_commands(self, commands: Sequence[tuple[CommandContract, object]]) -> None:
        for contract, command in commands:
            if not isinstance(command, contract.command_class):
                raise TypeError(f"Command does not match contract {contract.command_name!r}")
        self._staged_commands.extend(commands)

    async def save(self, repo_type: type, aggregate: object) -> None:
        self._pending_saves.append((repo_type, aggregate))
        self.stage_events(aggregate.pull_events())  # type: ignore[attr-defined]

    async def save_many(self, aggregates: Sequence[tuple[type, object]]) -> None:
        for repo_type, aggregate in aggregates:
            await self.save(repo_type, aggregate)

    @property
    def events(self) -> list[DomainEvent]:
        return list(self._staged_events)

    @property
    def committed_events(self) -> list[object]:
        return list(self._committed_events)

    @property
    def committed_commands(self) -> list[tuple[CommandContract, object]]:
        return list(self._committed_commands)

    def _committed_event_values(self) -> list[object]:
        return list(self._staged_events)

    async def __aenter__(self) -> InMemoryUnitOfWorkBase:
        self._committed = False
        self._staged_events = []
        self._committed_events = []
        self._staged_commands = []
        self._committed_commands = []
        self._pending_saves = []
        return self

    async def __aexit__(self, *args: object) -> None:
        if args[0] is None:
            await self.commit()
        else:
            await self.rollback()

    async def commit(self) -> None:
        resolved: dict[type, Any] = {}
        snapshots: dict[type, tuple[Any, Any]] = {}
        try:
            for repo_type, aggregate in self._pending_saves:
                if repo_type not in resolved:
                    repo = self.repository(repo_type)
                    resolved[repo_type] = repo
                    store = getattr(repo, "_store", None)
                    if store is not None:
                        snapshots[repo_type] = (repo, copy.deepcopy(store))
                await resolved[repo_type].save(aggregate)
            self._committed_events.extend(self._committed_event_values())
            self._committed_commands.extend(self._staged_commands)
            self._committed = True
        except BaseException:
            for repo, store in snapshots.values():
                self._restore_store(repo, store)
            raise
        finally:
            self._pending_saves.clear()
            self._staged_events.clear()
            self._staged_commands.clear()

    @staticmethod
    def _restore_store(repo: Any, snapshot: Any) -> None:
        """Restore a snapshot in place so every holder of the store observes it.

        Rebinding (``repo._store = snapshot``) would only swap the attribute on
        the resolved instance; instances sharing the same store object — e.g.
        when a subclass ``repository()`` returns a new instance per call —
        would keep observing the mutated state and the rollback would be fiction.
        """
        current = getattr(repo, "_store", None)
        if current is not None and hasattr(current, "clear") and hasattr(current, "update"):
            current.clear()
            current.update(snapshot)
        else:
            repo._store = snapshot

    async def rollback(self) -> None:
        self._pending_saves.clear()
        self._staged_events.clear()
        self._staged_commands.clear()
