from __future__ import annotations

import pytest
from pydantic import ValidationError

from shell.definition_service.framework.definition.graph_definition.api.semantic_query_request import (
    SemanticQueryRequest,
)
from shell.execution_service.framework.execution.edge_execution.api.create_edge_execution_request import (
    CreateEdgeExecutionRequest,
)
from shell.execution_service.framework.execution.workflow.api.create_workflow_request import (
    CreateWorkflowRequest,
)
from shell.ingestion_service.framework.ingestion.ingestion.api.create_ingestion_request import (
    CreateIngestionRequest,
)
from shell.platform.types import JsonStr
from shell.scheduling_service.framework.scheduling.scheduler_job.api.create_scheduler_job_request import (
    CreateSchedulerJobRequest,
)
from shell.user_service.framework.user.auth_session.api.login_auth_session_request import (
    LoginAuthSessionRequest,
)


@pytest.mark.parametrize(
    ("model", "payload", "field"),
    [
        (SemanticQueryRequest, {"query": "x" * 4001}, "query"),
        (
            CreateEdgeExecutionRequest,
            {"edge_definition_id": "x" * 256, "source_node_execution_id": "source"},
            "edge_definition_id",
        ),
        (
            CreateWorkflowRequest,
            {"session_id": "x" * 256, "project_id": "project"},
            "session_id",
        ),
        (
            CreateIngestionRequest,
            {
                "ingestion_data": JsonStr.from_object("x" * 100_001),
                "ingestion_context": JsonStr.from_object({}),
            },
            "ingestion_data",
        ),
        (
            CreateSchedulerJobRequest,
            {
                "scheduler_definition_id": "definition",
                "name": "job",
                "batch_size": 0,
            },
            "batch_size",
        ),
        (LoginAuthSessionRequest, {"email": "x"}, "email"),
    ],
)
def test_request_models_reject_invalid_or_oversized_values(
    model: type[object],
    payload: dict[str, object],
    field: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        model.model_validate(payload)

    assert field in str(error.value)


def test_request_models_accept_valid_payloads() -> None:
    assert SemanticQueryRequest(query="find workflows", limit=10).query == "find workflows"
    assert CreateWorkflowRequest(session_id="session-1", project_id="project-1")
    assert CreateIngestionRequest(
        ingestion_data=JsonStr.from_object({}),
        ingestion_context=JsonStr.from_object({}),
    ).ingestion_data
    assert CreateSchedulerJobRequest(
        scheduler_definition_id="definition-1",
        name="job-1",
    ).batch_size == 50