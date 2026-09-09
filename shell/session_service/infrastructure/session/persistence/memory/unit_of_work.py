from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from shell.platform.infrastructure.persistence.in_memory_unit_of_work import (
    InMemoryUnitOfWorkBase,
)
from shell.session_service.domain.session.aggregates.session.repositories.session_repository import (
    SessionRepository,
)
from shell.session_service.domain.session.aggregates.session_state.repositories.session_state_repository import (
    SessionStateRepository,
)
from shell.session_service.infrastructure.session.session.persistence.memory.in_memory_session_repository import (
    InMemorySessionRepository,
)
from shell.session_service.infrastructure.session.session_state.persistence.memory.in_memory_session_state_repository import (
    InMemorySessionStateRepository,
)

if TYPE_CHECKING:
    from shell.platform.infrastructure.mapping.integration_event_mapper import (
        IntegrationEventMapper,
    )

TRepository = TypeVar("TRepository")


class InMemorySessionUnitOfWork(InMemoryUnitOfWorkBase):
    def __init__(self, mapper: IntegrationEventMapper | None = None) -> None:
        super().__init__()
        self._session_repository = InMemorySessionRepository()
        self._session_state_repository = InMemorySessionStateRepository()
        if mapper is None:
            raise ValueError("InMemorySessionUnitOfWork requires an integration mapper")
        self._mapper = mapper

    def _committed_event_values(self) -> list[object]:
        return [self._mapper.map(event) for event in self._staged_events]

    def repository(self, repo_type: type[TRepository]) -> TRepository:
        repos: dict[type, object] = {
            InMemorySessionRepository: self._session_repository,
            SessionRepository: self._session_repository,
            InMemorySessionStateRepository: self._session_state_repository,
            SessionStateRepository: self._session_state_repository,
        }
        repo = repos.get(repo_type)
        if repo is None:
            msg = f"Unknown repository type: {repo_type}"
            raise ValueError(msg)
        return repo  # type: ignore[return-value]
