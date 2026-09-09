from __future__ import annotations

from shell.definition_service.application.definition.node_definition.commands.create_node_definition_command import (
    CreateNodeDefinitionCommand,
)
from shell.definition_service.application.definition.node_definition.queries.get_node_definition_by_id_query import (
    GetNodeDefinitionByIdQuery,
)
from shell.definition_service.framework.definition.node_definition.api.create_node_definition_request import (
    CreateNodeDefinitionRequest,
)
from shell.definition_service.framework.definition.node_definition.api.create_node_definition_response import (
    CreateNodeDefinitionResponse,
)
from shell.definition_service.framework.definition.node_definition.api.node_definition_response import (
    NodeDefinitionResponse,
)
from shell.platform.application.bus.command_bus import CommandBus
from shell.platform.application.bus.query_bus import QueryBus


class NodeDefinitionController:
    __slots__ = ("_command_bus", "_query_bus")

    def __init__(self, command_bus: CommandBus, query_bus: QueryBus) -> None:
        self._command_bus = command_bus
        self._query_bus = query_bus

    async def get_node_definition(self, node_definition_id: str) -> NodeDefinitionResponse | None:
        result = await self._query_bus.dispatch(
            GetNodeDefinitionByIdQuery(node_definition_id=node_definition_id)
        )
        if result is None:
            return None
        return NodeDefinitionResponse(
            id=result.id,
            node_type=result.node_type,
            node_position=result.node_position,
        )

    async def create_node_definition(
        self,
        body: CreateNodeDefinitionRequest,
    ) -> CreateNodeDefinitionResponse:
        node_definition_id = await self._command_bus.dispatch(
            CreateNodeDefinitionCommand(
                node_type=body.node_type,
                node_position=body.node_position,
                max_step=body.max_step,
            )
        )
        return CreateNodeDefinitionResponse(id=node_definition_id)
