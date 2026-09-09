from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from shell.definition_service.framework.definition.node_definition.api.controller import (
    NodeDefinitionController,
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
from shell.platform.framework.api.dependencies import get_command_bus, get_query_bus

router = APIRouter(prefix="/node-definitions", tags=["NodeDefinitions"])


def get_node_definition_controller(
    command_bus: CommandBus = Depends(get_command_bus),
    query_bus: QueryBus = Depends(get_query_bus),
) -> NodeDefinitionController:
    return NodeDefinitionController(command_bus, query_bus)


@router.get("/{node_definition_id}", response_model=NodeDefinitionResponse)
async def get_node_definition(
    node_definition_id: str,
    controller: NodeDefinitionController = Depends(get_node_definition_controller),
) -> NodeDefinitionResponse:
    response = await controller.get_node_definition(node_definition_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Node definition not found")
    return response


@router.post("/", response_model=CreateNodeDefinitionResponse, status_code=201)
async def create_node_definition(
    body: CreateNodeDefinitionRequest,
    controller: NodeDefinitionController = Depends(get_node_definition_controller),
) -> CreateNodeDefinitionResponse:
    return await controller.create_node_definition(body)
