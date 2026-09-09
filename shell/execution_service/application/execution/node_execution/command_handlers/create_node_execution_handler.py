from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.application.execution.node_execution.commands.create_node_execution_command import (
    CreateNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.exceptions.node_definition_not_found_error import (
    NodeDefinitionNotFoundError,
)
from shell.execution_service.domain.execution.aggregates.graph_execution.value_objects.graph_execution_id import (
    GraphExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_execution.node_execution import (
    NodeExecution,
)
from shell.execution_service.domain.execution.aggregates.node_execution.repositories.node_execution_repository import (
    NodeExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
    NodeDefinitionIdRef,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_execution_id import (
    NodeExecutionId,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.node_link_execution import (
    NodeLinkExecution,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.repositories.node_link_execution_repository import (
    NodeLinkExecutionRepository,
)
from shell.execution_service.domain.execution.aggregates.node_link_execution.value_objects.node_link_execution_id import (
    NodeLinkExecutionId,
)
from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.domain.value_objects.created_at import CreatedAt

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.node_execution.ports.node_definition_reader import (
        NodeDefinitionReader,
    )
    from shell.platform.application.ports.persistence.unit_of_work import UnitOfWork
    from shell.platform.domain.ports.identity import IdGenerator
    from shell.platform.domain.ports.time import Clock


class CreateNodeExecutionHandler(CommandHandler[CreateNodeExecutionCommand]):
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        id_generator: IdGenerator,
        clock: Clock,
        node_definition_reader: NodeDefinitionReader,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._id_generator = id_generator
        self._clock = clock
        self._node_definition_reader = node_definition_reader

    async def handle(
        self,
        command: CreateNodeExecutionCommand,
    ) -> str:
        node_definition_id = NodeDefinitionIdRef(command.node_definition_id)
        node_definition = await self._node_definition_reader.get_node_definition(
            node_definition_id
        )
        if node_definition is None:
            raise NodeDefinitionNotFoundError(command.node_definition_id)

        now = CreatedAt.from_datetime(self._clock.now())
        node_execution = NodeExecution.create(
            id=self._id_generator.new_id(NodeExecutionId),
            graph_execution_id=GraphExecutionId(command.graph_execution_id),
            node_definition_id=node_definition.node_definition_id,
            node_position=node_definition.node_position,
            node_type=node_definition.node_type,
            now=now,
        )
        node_execution_link = NodeLinkExecution.create(
            id_=self._id_generator.new_id(NodeLinkExecutionId),
            graph_execution_id=GraphExecutionId(command.graph_execution_id),
            node_execution_id=node_execution.id,
            now=now,
        )

        async with self._unit_of_work as unit_of_work:
            await unit_of_work.save_many(
                (
                    (NodeExecutionRepository, node_execution),
                    (NodeLinkExecutionRepository, node_execution_link),
                )
            )
            await unit_of_work.commit()

        return node_execution.id.value
