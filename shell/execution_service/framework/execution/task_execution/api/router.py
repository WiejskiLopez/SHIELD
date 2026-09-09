"""Task executions router — query task executions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from shell.execution_service.framework.execution.task_execution.api.controller import (
    TaskExecutionController,
)
from shell.execution_service.framework.execution.task_execution.api.task_execution_response import (
    TaskExecutionResponse,
)
from shell.platform.framework.api.dependencies import ContainerProtocol, get_core_container
from shell.platform.framework.api.models.page import Page

router = APIRouter(prefix="/task-executions", tags=["Task Executions"])


def get_task_execution_controller(
    container: ContainerProtocol = Depends(get_core_container),
) -> TaskExecutionController:
    command_bus = container.app.buses.command_bus if hasattr(container, "app") else container.command_bus()
    query_bus = container.app.buses.query_bus if hasattr(container, "app") else container.query_bus()
    return TaskExecutionController(command_bus, query_bus)


@router.get("", response_model=Page[TaskExecutionResponse])
async def list_task_executions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000, alias="page_size"),
    controller: TaskExecutionController = Depends(get_task_execution_controller),
) -> Page[TaskExecutionResponse]:
    return await controller.list_task_executions(page=page, page_size=page_size)


@router.post("/{task_execution_id}:start", status_code=204)
async def start_task_execution(task_execution_id: str, controller: TaskExecutionController = Depends(get_task_execution_controller)) -> None:
    await controller.start_task_execution(task_execution_id)


@router.post("/{task_execution_id}:complete", status_code=204)
async def complete_task_execution(task_execution_id: str, controller: TaskExecutionController = Depends(get_task_execution_controller)) -> None:
    await controller.complete_task_execution(task_execution_id)


@router.post("/{task_execution_id}:fail", status_code=204)
async def fail_task_execution(task_execution_id: str, controller: TaskExecutionController = Depends(get_task_execution_controller)) -> None:
    await controller.fail_task_execution(task_execution_id)


@router.post("/{task_execution_id}:timeout", status_code=204)
async def timeout_task_execution(task_execution_id: str, controller: TaskExecutionController = Depends(get_task_execution_controller)) -> None:
    await controller.timeout_task_execution(task_execution_id)


@router.post("/{task_execution_id}:exhaust", status_code=204)
async def exhaust_task_execution(task_execution_id: str, controller: TaskExecutionController = Depends(get_task_execution_controller)) -> None:
    await controller.exhaust_task_execution(task_execution_id)
