from __future__ import annotations

from typing import TypeVar

from shell.definition_service.domain.definition.aggregates.graph_definition.repositories.graph_definition_repository import (
    GraphDefinitionRepository,
)
from shell.definition_service.domain.definition.aggregates.graph_definition_embedding.repositories.graph_definition_embedding_repository import (
    GraphDefinitionEmbeddingRepository,
)
from shell.definition_service.domain.definition.aggregates.node_definition.repositories.node_definition_repository import (
    NodeDefinitionRepository,
)
from shell.definition_service.domain.definition.aggregates.node_link_definition.repositories.node_link_definition_repository import (
    NodeLinkDefinitionRepository,
)
from shell.definition_service.domain.definition.aggregates.runner_config.repositories.runner_config_repository import (
    RunnerConfigRepository,
)
from shell.definition_service.infrastructure.definition.graph_definition.persistence.memory.in_memory_graph_definition_repository import (
    InMemoryGraphDefinitionRepository,
)
from shell.definition_service.infrastructure.definition.graph_definition_embedding.persistence.memory.in_memory_graph_definition_embedding_repository import (
    InMemoryGraphDefinitionEmbeddingRepository,
)
from shell.definition_service.infrastructure.definition.node_definition.persistence.memory.in_memory_node_definition_repository import (
    InMemoryNodeDefinitionRepository,
)
from shell.definition_service.infrastructure.definition.node_link_definition.persistence.memory.in_memory_node_link_definition_repository import (
    InMemoryNodeLinkDefinitionRepository,
)
from shell.definition_service.infrastructure.definition.runner_config.persistence.memory.in_memory_runner_config_repository import (
    InMemoryRunnerConfigRepository,
)
from shell.platform.infrastructure.persistence.in_memory_unit_of_work import (
    InMemoryUnitOfWorkBase,
)

TRepository = TypeVar("TRepository")


class InMemoryDefinitionUnitOfWork(InMemoryUnitOfWorkBase):
    def __init__(self) -> None:
        super().__init__()
        self._runner_config_repository = InMemoryRunnerConfigRepository()
        self._graph_definition_repository = InMemoryGraphDefinitionRepository()
        self._node_definition_repository = InMemoryNodeDefinitionRepository()
        self._node_link_definition_repository = InMemoryNodeLinkDefinitionRepository()
        self._node_definition_repository.set_link_repository(self._node_link_definition_repository)
        self._graph_definition_embedding_repository = InMemoryGraphDefinitionEmbeddingRepository()

    def repository(self, repo_type: type[TRepository]) -> TRepository:
        repos: dict[type, object] = {
            InMemoryRunnerConfigRepository: self._runner_config_repository,
            RunnerConfigRepository: self._runner_config_repository,
            InMemoryGraphDefinitionRepository: self._graph_definition_repository,
            GraphDefinitionRepository: self._graph_definition_repository,
            InMemoryNodeDefinitionRepository: self._node_definition_repository,
            NodeDefinitionRepository: self._node_definition_repository,
            InMemoryNodeLinkDefinitionRepository: self._node_link_definition_repository,
            NodeLinkDefinitionRepository: self._node_link_definition_repository,
            InMemoryGraphDefinitionEmbeddingRepository: self._graph_definition_embedding_repository,
            GraphDefinitionEmbeddingRepository: self._graph_definition_embedding_repository,
        }
        repo = repos.get(repo_type)
        if repo is None:
            msg = f"Unknown repository type: {repo_type}"
            raise ValueError(msg)
        return repo  # type: ignore[return-value]
