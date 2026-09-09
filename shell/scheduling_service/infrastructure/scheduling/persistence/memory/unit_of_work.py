from __future__ import annotations

from typing import TypeVar

from shell.platform.infrastructure.persistence.in_memory_unit_of_work import (
    InMemoryUnitOfWorkBase,
)
from shell.scheduling_service.domain.scheduling.aggregates.scheduler_definition.repositories.scheduler_definition_repository import (
    SchedulerDefinitionRepository,
)
from shell.scheduling_service.domain.scheduling.aggregates.scheduler_execution.repositories.scheduler_execution_repository import (
    SchedulerExecutionRepository,
)
from shell.scheduling_service.domain.scheduling.aggregates.scheduler_job.repositories.scheduler_job_repository import (
    SchedulerJobRepository,
)
from shell.scheduling_service.infrastructure.scheduling.scheduler_definition.persistence.memory.in_memory_scheduler_definition_repository import (
    InMemorySchedulerDefinitionRepository,
)
from shell.scheduling_service.infrastructure.scheduling.scheduler_execution.persistence.memory.in_memory_scheduler_execution_repository import (
    InMemorySchedulerExecutionRepository,
)
from shell.scheduling_service.infrastructure.scheduling.scheduler_job.persistence.memory.in_memory_scheduler_job_repository import (
    InMemorySchedulerJobRepository,
)

TRepository = TypeVar("TRepository")


class InMemorySchedulingUnitOfWork(InMemoryUnitOfWorkBase):
    def __init__(self) -> None:
        super().__init__()
        self._scheduler_definition_repository = InMemorySchedulerDefinitionRepository()
        self._scheduler_execution_repository = InMemorySchedulerExecutionRepository()
        self._scheduler_job_repository = InMemorySchedulerJobRepository()

    def repository(self, repo_type: type[TRepository]) -> TRepository:
        repos: dict[type, object] = {
            InMemorySchedulerDefinitionRepository: self._scheduler_definition_repository,
            SchedulerDefinitionRepository: self._scheduler_definition_repository,
            InMemorySchedulerExecutionRepository: self._scheduler_execution_repository,
            SchedulerExecutionRepository: self._scheduler_execution_repository,
            InMemorySchedulerJobRepository: self._scheduler_job_repository,
            SchedulerJobRepository: self._scheduler_job_repository,
        }
        repo = repos.get(repo_type)
        if repo is None:
            msg = f"Unknown repository type: {repo_type}"
            raise ValueError(msg)
        return repo  # type: ignore[return-value]
