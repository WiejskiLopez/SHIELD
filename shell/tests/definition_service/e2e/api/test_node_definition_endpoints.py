from __future__ import annotations

from typing import TYPE_CHECKING

from httpx import ASGITransport, AsyncClient

from shell.tests.definition_service.e2e.conftest import TEST_API_KEY, make_definition_app

if TYPE_CHECKING:
    import pathlib


class TestNodeDefinitionEndpoints:
    async def test_get_node_definition_returns_type_and_position(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        app = await make_definition_app(tmp_path)
        headers = {"X-API-Key": TEST_API_KEY}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_response = await client.post(
                "/api/v1/node-definitions/",
                json={"node_type": "worker", "node_position": 2},
                headers=headers,
            )
            node_definition_id = create_response.json()["id"]
            response = await client.get(
                f"/api/v1/node-definitions/{node_definition_id}",
                headers=headers,
            )

        assert response.status_code == 200
        assert response.json()["node_type"] == "worker"
        assert response.json()["node_position"] == 2

    async def test_create_node_definition_persists_position(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        app = await make_definition_app(tmp_path)
        headers = {"X-API-Key": TEST_API_KEY}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/node-definitions/",
                json={"node_type": "worker", "node_position": 2, "max_step": 8},
                headers=headers,
            )

        assert response.status_code == 201
        assert response.json()["id"]

    async def test_create_node_definition_rejects_negative_position(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        app = await make_definition_app(tmp_path)
        headers = {"X-API-Key": TEST_API_KEY}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/node-definitions/",
                json={"node_type": "worker", "node_position": -1},
                headers=headers,
            )

        assert response.status_code == 422

    async def test_create_node_definition_requires_api_key(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        app = await make_definition_app(tmp_path)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/node-definitions/",
                json={"node_type": "worker", "node_position": 1},
            )

        assert response.status_code == 401
