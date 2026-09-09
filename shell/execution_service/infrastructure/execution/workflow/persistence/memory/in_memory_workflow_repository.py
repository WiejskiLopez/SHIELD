from __future__ import annotations

from typing import TYPE_CHECKING

from shell.execution_service.domain.execution.aggregates.workflow import Workflow
from shell.execution_service.domain.execution.aggregates.workflow.repositories.workflow_repository import (
    WorkflowRepository,
)
from shell.execution_service.domain.execution.aggregates.workflow.value_objects.workflow_id import (
    WorkflowId,
)
from shell.platform.infrastructure.persistence.in_memory_repository import (
    InMemoryRepository,
)

if TYPE_CHECKING:
    from shell.execution_service.domain.execution.aggregates.session_execution.value_objects.session_id_ref import (
        SessionIdRef,
    )


class InMemoryWorkflowRepository(InMemoryRepository[Workflow, WorkflowId], WorkflowRepository):
    async def get_by_id(self, id: WorkflowId) -> Workflow | None:
        workflow = self._store.get(id.value)
        if workflow is None or workflow.deleted_at.value is not None:
            return None
        return workflow

    async def get_by_session_id(self, session_id: SessionIdRef) -> list[Workflow]:
        return [
            wf
            for wf in self._visible_values()
            if wf.deleted_at.value is None and wf.session_id == session_id
        ]
