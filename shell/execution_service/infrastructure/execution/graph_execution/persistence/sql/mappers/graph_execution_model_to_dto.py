"""Map GraphExecution persistence models to application query DTOs."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from shell.execution_service.application.execution.graph_execution.dto.graph_execution_dto import (
    GraphExecutionDto,
)
from shell.platform.types import JsonStr

if TYPE_CHECKING:
    from shell.execution_service.infrastructure.execution.graph_execution.persistence.sql.models.graph_execution import (
        GraphExecutionModel,
    )


def graph_execution_model_to_dto(model: GraphExecutionModel) -> GraphExecutionDto:
    return GraphExecutionDto(
        id=model.id,
        graph_definition_id=model.graph_definition_id,
        task_execution_id=model.task_execution_id,
        parent_graph_execution_id=model.parent_graph_execution_id,
        state_data=JsonStr(
            json.dumps({"input": model.state_input, "output": model.state_output})
        ),
        depth=model.depth,
        timeout_at=model.timeout_at,
    )
