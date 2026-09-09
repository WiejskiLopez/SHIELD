from __future__ import annotations

import pytest

from shell.definition_service.application.definition.node_definition.command_handlers.create_node_definition_handler import (
    CreateNodeDefinitionHandler,
)
from shell.definition_service.application.definition.node_definition.commands.create_node_definition_command import (
    CreateNodeDefinitionCommand,
)
from shell.definition_service.domain.definition.aggregates.node_definition.events.node_definition_created_event import (
    NodeDefinitionCreatedEvent,
)
from shell.definition_service.domain.definition.aggregates.node_definition.value_objects.node_definition_id import (
    NodeDefinitionId,
)
from shell.definition_service.infrastructure.definition.node_definition.persistence.memory.in_memory_node_definition_repository import (
    InMemoryNodeDefinitionRepository,
)
from shell.platform.application.exceptions.command_validation_error import RequiredCommandFieldError


async def test_create_node_definition_handler_persists_position_and_event(
    unit_of_work,
    clock,
    id_generator,
) -> None:
    handler = CreateNodeDefinitionHandler(unit_of_work, clock, id_generator)

    node_definition_id = await handler.handle(
        CreateNodeDefinitionCommand(
            node_type="worker",
            node_position=3,
            max_step=12,
        )
    )

    repository = unit_of_work.repository(InMemoryNodeDefinitionRepository)
    node_definition = await repository.get_by_id(NodeDefinitionId(node_definition_id))

    assert node_definition is not None
    assert node_definition.node_type.value == "worker"
    assert node_definition.node_position.value == 3
    assert node_definition.max_step is not None
    assert node_definition.max_step.value == 12
    assert any(
        isinstance(event, NodeDefinitionCreatedEvent)
        for event in unit_of_work.committed_events
    )


def test_create_node_definition_command_requires_node_type() -> None:
    with pytest.raises(RequiredCommandFieldError):
        CreateNodeDefinitionCommand(node_type="", node_position=0)

