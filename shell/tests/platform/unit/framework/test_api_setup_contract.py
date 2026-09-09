"""Contract tests for the shared HTTP application setup."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shell.platform.framework.api.middleware.api_key import AuthMiddleware
from shell.platform.framework.api.setup import setup_api_common


def _app() -> FastAPI:
    app = FastAPI(title="contract", version="0.1.0")

    @app.get("/protected")
    async def protected() -> dict[str, str]:
        return {"status": "protected"}

    setup_api_common(
        app,
        api_key="contract-key",
        allowed_origins=["https://frontend.example"],
        public_exact={"/health", "/api"},
        public_prefix={"/docs", "/redoc", "/openapi.json"},
    )
    return app


async def test_common_setup_exposes_public_contract_and_rejects_missing_auth() -> None:
    app = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        discovery = await client.get("/api")
        unauthorized = await client.get("/protected")
        authorized = await client.get(
            "/protected",
            headers={"X-API-Key": "contract-key", "X-Causation-Id": "cause-1"},
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert discovery.status_code == 200
    assert discovery.json()["latest"] == "v1"
    assert unauthorized.status_code == 401
    assert unauthorized.json()["status"] == 401
    assert authorized.status_code == 200
    assert authorized.json() == {"status": "protected"}
    assert authorized.headers["X-Correlation-ID"]
    assert authorized.headers["X-Causation-ID"] == "cause-1"


def test_common_setup_fail_closed_without_credentials() -> None:
    app = FastAPI(title="contract", version="0.1.0")

    @app.get("/protected")
    async def protected() -> dict[str, str]:
        return {"status": "protected"}

    with pytest.raises(ValueError, match="fail-closed"):
        setup_api_common(app)


def test_common_setup_accepts_jwt_only_or_session_factory_only() -> None:
    for kwargs in (
        {"jwt_secret": "jwt-secret"},
        {"session_query_factory": lambda token: object()},
    ):
        app = FastAPI(title="contract", version="0.1.0")

        @app.get("/protected")
        async def protected() -> dict[str, str]:
            return {"status": "protected"}

        setup_api_common(app, **kwargs)


def test_auth_middleware_guard_rejects_empty_credentials() -> None:
    app = FastAPI(title="contract", version="0.1.0")
    with pytest.raises(ValueError, match="fail-closed"):
        AuthMiddleware(app)


async def test_common_setup_explicit_opt_out_leaves_protected_open() -> None:
    app = FastAPI(title="contract", version="0.1.0")

    @app.get("/protected")
    async def protected() -> dict[str, str]:
        return {"status": "protected"}

    setup_api_common(app, auth_enabled=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/protected")

    assert response.status_code == 200


async def test_common_setup_registers_cors_and_shared_openapi_schemas() -> None:
    app = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/protected",
            headers={
                "Origin": "https://frontend.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        openapi = await client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://frontend.example"
    schemas = openapi.json()["components"]["schemas"]
    assert {"ProblemDetail", "Page", "FieldError"}.issubset(schemas)
