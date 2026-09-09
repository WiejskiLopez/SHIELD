"""Fail-closed auth for the GraphDefinition aggregate standalone app."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from shell.definition_service.framework.definition.graph_definition.api.app import (
    create_graph_definition_app,
)


def test_graph_definition_app_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="fail-closed"):
        create_graph_definition_app(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fail-closed"):
        create_graph_definition_app(object(), api_key="")  # type: ignore[arg-type]


async def test_graph_definition_app_health_public_and_api_protected() -> None:
    app = create_graph_definition_app(object(), api_key="agg-key")  # type: ignore[arg-type]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        guarded = await client.get("/nonexistent-route")
        authorized = await client.get("/nonexistent-route", headers={"X-API-Key": "agg-key"})

    assert health.status_code == 200
    assert guarded.status_code == 401
    assert authorized.status_code == 404
