"""Fail-closed auth for the execution aggregate standalone apps."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from shell.execution_service.framework.execution.edge_execution.api.app import (
    create_edge_execution_app,
)
from shell.execution_service.framework.execution.edge_link_execution.api.app import (
    create_edge_link_execution_app,
)
from shell.execution_service.framework.execution.node_execution.api.app import (
    create_node_execution_app,
)
from shell.execution_service.framework.execution.workflow.api.app import (
    create_workflow_app,
)

FACTORIES = (
    create_edge_execution_app,
    create_edge_link_execution_app,
    create_node_execution_app,
    create_workflow_app,
)


@pytest.mark.parametrize("factory", FACTORIES)
def test_aggregate_app_rejects_empty_key(factory) -> None:
    with pytest.raises(ValueError, match="fail-closed"):
        factory(object())
    with pytest.raises(ValueError, match="fail-closed"):
        factory(object(), api_key="")


@pytest.mark.parametrize("factory", FACTORIES)
async def test_aggregate_app_health_public_and_api_protected(factory) -> None:
    app = factory(object(), api_key="agg-key")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        guarded = await client.get("/nonexistent-route")
        authorized = await client.get("/nonexistent-route", headers={"X-API-Key": "agg-key"})

    assert health.status_code == 200
    assert guarded.status_code == 401
    assert authorized.status_code == 404
