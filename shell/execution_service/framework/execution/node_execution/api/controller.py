from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from shell.execution_service.application.execution.node_execution.commands.complete_node_execution_command import (
    CompleteNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.commands.create_node_execution_command import (
    CreateNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.commands.delete_node_execution_command import (
    DeleteNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.commands.fail_node_execution_command import (
    FailNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.commands.retry_node_execution_command import (
    RetryNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.commands.start_node_execution_command import (
    StartNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.commands.timeout_node_execution_command import (
    TimeoutNodeExecutionCommand,
)
from shell.execution_service.application.execution.node_execution.exceptions.node_execution_not_found_error import (
    NodeExecutionNotFoundError,
)
from shell.execution_service.application.execution.node_execution.queries.get_node_execution_by_id_query import (
    GetNodeExecutionByIdQuery,
)
from shell.execution_service.application.execution.node_execution.queries.get_node_execution_result_query import (
    GetNodeExecutionResultQuery,
)
from shell.execution_service.framework.execution.node_execution.api.create_node_execution_request import (
    CreateNodeExecutionRequest as ApiCreateNodeExecutionRequest,
)
from shell.execution_service.framework.execution.node_execution.api.create_node_execution_response import (
    CreateNodeExecutionResponse as ApiCreateNodeExecutionResponse,
)
from shell.execution_service.framework.execution.node_execution.api.node_execution_response import (
    NodeExecutionResponse as ApiNodeExecutionResponse,
)
from shell.execution_service.framework.execution.node_execution.api.node_execution_result_response import (
    NodeExecutionResultResponse,
)

if TYPE_CHECKING:
    from shell.platform.application.bus.command_bus import CommandBus
    from shell.platform.application.bus.query_bus import QueryBus


class NodeExecutionController:
    __slots__ = ("_command_bus", "_query_bus")

    def __init__(self, command_bus: CommandBus, query_bus: QueryBus) -> None:
        self._command_bus = command_bus
        self._query_bus = query_bus

    async def get_node_execution(self, node_execution_id: str) -> ApiNodeExecutionResponse:
        result = await self._query_bus.dispatch(
            GetNodeExecutionByIdQuery(node_execution_id=node_execution_id)
        )
        if result is None:
            raise HTTPException(
                status_code=404, detail=f"NodeExecution '{node_execution_id}' not found"
            )
        return ApiNodeExecutionResponse(
            id=result.id,
            node_type=result.node_type,
        )

    async def get_node_execution_result(
        self, node_execution_id: str, workflow_id: str
    ) -> NodeExecutionResultResponse:
        result = await self._query_bus.dispatch(
            GetNodeExecutionResultQuery(
                node_execution_id=node_execution_id, workflow_id=workflow_id
            )
        )
        if result is None:
            raise HTTPException(
                status_code=404, detail=f"NodeResult for '{node_execution_id}' not found"
            )
        return NodeExecutionResultResponse(
            node_execution_id=node_execution_id,
            workflow_id=workflow_id,
            status=str(result),
        )

    async def create_node_execution(
        self, body: ApiCreateNodeExecutionRequest
    ) -> ApiCreateNodeExecutionResponse:
        node_execution_id = await self._command_bus.dispatch(
            CreateNodeExecutionCommand(
                graph_execution_id=body.graph_execution_id,
                node_definition_id=body.node_definition_id,
            )
        )
        return ApiCreateNodeExecutionResponse(id=node_execution_id)

    async def delete_node_execution(self, node_execution_id: str) -> None:
        try:
            await self._command_bus.dispatch(
                DeleteNodeExecutionCommand(node_execution_id=node_execution_id)
            )
        except NodeExecutionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def start_node_execution(self, node_execution_id: str) -> None:
        await self._command_bus.dispatch(StartNodeExecutionCommand(node_execution_id=node_execution_id))

    async def complete_node_execution(self, node_execution_id: str) -> None:
        await self._command_bus.dispatch(CompleteNodeExecutionCommand(node_execution_id=node_execution_id))

    async def fail_node_execution(self, node_execution_id: str) -> None:
        await self._command_bus.dispatch(FailNodeExecutionCommand(node_execution_id=node_execution_id))

    async def retry_node_execution(self, node_execution_id: str) -> None:
        await self._command_bus.dispatch(RetryNodeExecutionCommand(node_execution_id=node_execution_id))

    async def timeout_node_execution(self, node_execution_id: str) -> None:
        await self._command_bus.dispatch(TimeoutNodeExecutionCommand(node_execution_id=node_execution_id))
