"""Unit tests for HTTP causation-id propagation."""

from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shell.platform.application.context.causation_id import get_causation_id
from shell.platform.framework.api.middleware.causation_id import CausationIdMiddleware


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/echo")
    async def echo() -> dict[str, str]:
        return {"causation_id": get_causation_id()}

    app.add_middleware(CausationIdMiddleware)
    return app


async def test_propagates_causation_id_header_and_context() -> None:
    app = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/echo", headers={"X-Causation-Id": "cause-123"})

    assert response.status_code == 200
    assert response.json() == {"causation_id": "cause-123"}
    assert response.headers["X-Causation-Id"] == "cause-123"


async def test_ignores_causation_id_with_control_characters() -> None:
    app = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/echo", headers={"X-Causation-Id": "bad\r\nvalue"})

    assert response.status_code == 200
    assert response.json() == {"causation_id": ""}
    assert "X-Causation-Id" not in response.headers
