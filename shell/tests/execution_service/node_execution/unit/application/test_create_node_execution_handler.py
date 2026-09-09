from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shell.execution_service.application.execution.node_execution.command_handlers.create_node_execution_handler import (
    CreateNodeExecutionHandler,
)
from shell.execution_service.application.execution.node_execution.commands.create_node_execution_command import (
    CreateNodeExecutionCommand,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_reference import (
    NodeDefinitionReference,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_position import (
    NodePosition,
)
from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_type import (
    NodeType,
)
from shell.platform.infrastructure.persistence.memory import FakeClock, FakeIdGenerator

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.node_execution.value_objects.node_definition_id_ref import (
        NodeDefinitionIdRef,
    )


class FakeNodeDefinitionReader:
    async def get_node_definition(self, node_definition_id: NodeDefinitionIdRef):
        return NodeDefinitionReference(
            node_definition_id=node_definition_id,
            node_type=NodeType("worker"),
            node_position=NodePosition(7),
        )


class FakeEventBus:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, events) -> None:
        self.events.extend(events)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.aggregates = []
        self.events = []
        self.save_calls = 0
        self.save_many_calls = 0
        self.commit_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def save(self, _repository, aggregate) -> None:
        self.save_calls += 1
        self.aggregates.append(aggregate)
        self.events.extend(aggregate.pull_events())

    async def save_many(self, aggregates) -> None:
        self.save_many_calls += 1
        for _repository, aggregate in aggregates:
            self.aggregates.append(aggregate)
            self.events.extend(aggregate.pull_events())

    async def commit(self) -> None:
        self.commit_calls += 1


async def test_create_handler_reads_type_and_position_from_node_definition() -> None:
    unit_of_work = FakeUnitOfWork()
    handler = CreateNodeExecutionHandler(
        unit_of_work=unit_of_work,
        id_generator=FakeIdGenerator(),
        clock=FakeClock(datetime(2024, 1, 1, tzinfo=UTC)),
        node_definition_reader=FakeNodeDefinitionReader(),
    )

    await handler.handle(
        CreateNodeExecutionCommand(
            graph_execution_id="graph-1",
            node_definition_id="definition-1",
        )
    )

    node_execution = unit_of_work.aggregates[0]
    node_link_execution = unit_of_work.aggregates[1]
    assert node_execution.node_type.value == "worker"
    assert node_execution.node_position.value == 7
    assert unit_of_work.commit_calls == 1
    assert node_execution.node_definition_id.value == "definition-1"
    assert node_link_execution.node_execution_id == node_execution.id
    assert node_link_execution.graph_execution_id.value == "graph-1"
    assert unit_of_work.save_calls == 0
    assert unit_of_work.save_many_calls == 1
