from __future__ import annotations

from typing import TYPE_CHECKING

from shell.definition_service.application.definition.node_definition.commands.create_node_definition_command import (
    CreateNodeDefinitionCommand,
)
from shell.definition_service.domain.definition.aggregates.node_definition.node_definition import (
    NodeDefinition,
)
from shell.definition_service.domain.definition.aggregates.node_definition.repositories.node_definition_repository import (
    NodeDefinitionRepository,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.max_step import (
    MaxStep,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_definition_id import (
    NodeDefinitionId,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_position import (
    NodePosition,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_type import (
    NodeType,
)
from shell.platform.application.command_handlers.command_handler import CommandHandler
from shell.platform.domain.value_objects.created_at import CreatedAt

if TYPE_CHECKING:
    from shell.platform.application.ports.persistence.unit_of_work import UnitOfWork
    from shell.platform.domain.ports.identity import IdGenerator
    from shell.platform.domain.ports.time import Clock


class CreateNodeDefinitionHandler(CommandHandler[CreateNodeDefinitionCommand]):
    def __init__(self, unit_of_work: UnitOfWork, clock: Clock, id_generator: IdGenerator) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, command: CreateNodeDefinitionCommand) -> str:
        node_definition_id = self._id_generator.new_id(NodeDefinitionId)
        node_definition = NodeDefinition.create(
            id=node_definition_id,
            now=CreatedAt.from_datetime(self._clock.now()),
            node_type=NodeType(command.node_type),
            node_position=NodePosition(command.node_position),
            max_step=MaxStep(command.max_step) if command.max_step is not None else None,
        )
        async with self._unit_of_work as unit_of_work:
            await unit_of_work.save(NodeDefinitionRepository, node_definition)
            await unit_of_work.commit()
        return node_definition_id.value
