from __future__ import annotations

from typing import TypeVar

from shell.platform.infrastructure.persistence.in_memory_unit_of_work import (
    InMemoryUnitOfWorkBase,
)
from shell.user_service.domain.user.aggregates.auth_session.repositories.auth_session_repository import (
    AuthSessionRepository,
)
from shell.user_service.domain.user.aggregates.user.repositories.user_repository import (
    UserRepository,
)
from shell.user_service.infrastructure.user.auth_session.persistence.memory.in_memory_auth_session_repository import (
    InMemoryAuthSessionRepository,
)
from shell.user_service.infrastructure.user.user.persistence.memory.in_memory_user_repository import (
    InMemoryUserRepository,
)

TRepository = TypeVar("TRepository")


class InMemoryUserUnitOfWork(InMemoryUnitOfWorkBase):
    def __init__(self) -> None:
        super().__init__()
        self._user_repository = InMemoryUserRepository()
        self._auth_session_repository = InMemoryAuthSessionRepository()

    def repository(self, repo_type: type[TRepository]) -> TRepository:
        repos: dict[type, object] = {
            InMemoryUserRepository: self._user_repository,
            UserRepository: self._user_repository,
            InMemoryAuthSessionRepository: self._auth_session_repository,
            AuthSessionRepository: self._auth_session_repository,
        }
        repo = repos.get(repo_type)
        if repo is None:
            raise ValueError(f"Unknown repository type: {repo_type}")
        return repo  # type: ignore[return-value]
