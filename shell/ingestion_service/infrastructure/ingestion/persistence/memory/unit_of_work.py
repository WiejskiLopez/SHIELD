from __future__ import annotations

from typing import TypeVar

from shell.ingestion_service.domain.ingestion.aggregates.ingestion.repositories.ingestion_repository import (
    IngestionRepository,
)
from shell.ingestion_service.infrastructure.ingestion.persistence.memory.in_memory_ingestion_repository import (
    InMemoryIngestionRepository,
)
from shell.platform.infrastructure.persistence.in_memory_unit_of_work import (
    InMemoryUnitOfWorkBase,
)

TRepository = TypeVar("TRepository")


class InMemoryIngestionUnitOfWork(InMemoryUnitOfWorkBase):
    def __init__(self) -> None:
        super().__init__()
        self._ingestion_repository = InMemoryIngestionRepository()

    def repository(self, repo_type: type[TRepository]) -> TRepository:
        repos: dict[type, object] = {
            InMemoryIngestionRepository: self._ingestion_repository,
            IngestionRepository: self._ingestion_repository,
        }
        repo = repos.get(repo_type)
        if repo is None:
            raise ValueError(f"Unknown repository type: {repo_type}")
        return repo  # type: ignore[return-value]
