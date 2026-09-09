from __future__ import annotations

from typing import TypeVar

from shell.platform.infrastructure.persistence.in_memory_unit_of_work import (
    InMemoryUnitOfWorkBase,
)
from shell.project_service.domain.project.aggregates.project.repositories.project_repository import (
    ProjectRepository,
)
from shell.project_service.domain.project.aggregates.project_skill.repositories.project_skill_repository import (
    ProjectSkillRepository,
)
from shell.project_service.domain.project.aggregates.project_state.repositories.project_state_repository import (
    ProjectStateRepository,
)
from shell.project_service.infrastructure.project.project.persistence.memory.in_memory_project_repository import (
    InMemoryProjectRepository,
)
from shell.project_service.infrastructure.project.project_skill.persistence.memory.in_memory_project_skill_repository import (
    InMemoryProjectSkillRepository,
)
from shell.project_service.infrastructure.project.project_state.persistence.memory.in_memory_project_state_repository import (
    InMemoryProjectStateRepository,
)

TRepository = TypeVar("TRepository")


class InMemoryProjectUnitOfWork(InMemoryUnitOfWorkBase):
    def __init__(self) -> None:
        super().__init__()
        self._project_repository = InMemoryProjectRepository()
        self._project_skill_repository = InMemoryProjectSkillRepository()
        self._project_state_repository = InMemoryProjectStateRepository()

    def repository(self, repo_type: type[TRepository]) -> TRepository:
        repos: dict[type, object] = {
            InMemoryProjectRepository: self._project_repository,
            ProjectRepository: self._project_repository,
            InMemoryProjectSkillRepository: self._project_skill_repository,
            ProjectSkillRepository: self._project_skill_repository,
            InMemoryProjectStateRepository: self._project_state_repository,
            ProjectStateRepository: self._project_state_repository,
        }
        repo = repos.get(repo_type)
        if repo is None:
            raise ValueError(f"Unknown repository type: {repo_type}")
        return repo  # type: ignore[return-value]
