from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from shell.execution_service.domain.execution.aggregates.session_execution.value_objects.session_id_ref import (
    SessionIdRef,
)
from shell.execution_service.domain.execution.aggregates.session_execution.value_objects.session_reference import (
    SessionReference,
)
from shell.execution_service.infrastructure.execution.session_execution.adapters.session_reader.session_reader_http_adapter import (
    SessionReaderHttpAdapter,
)


class TestSessionReaderHttpAdapter:
    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        return AsyncMock(spec="httpx.AsyncClient")

    @pytest.fixture
    def adapter(self, mock_client: AsyncMock) -> SessionReaderHttpAdapter:
        return SessionReaderHttpAdapter(client=mock_client)

    async def test_get_by_id_returns_none_on_404(
        self,
        adapter: SessionReaderHttpAdapter,
        mock_client: AsyncMock,
    ) -> None:
        mock_client.get = AsyncMock(return_value=Mock(status_code=404))
        result = await adapter.get_by_id(SessionIdRef("nonexistent-session"))
        assert result is None

    async def test_get_by_id_maps_response(
        self,
        adapter: SessionReaderHttpAdapter,
        mock_client: AsyncMock,
    ) -> None:
        response_data = {
            "id": "session-1",
        }
        mock_client.get = AsyncMock(
            return_value=Mock(status_code=200, json=Mock(return_value=response_data))
        )
        result = await adapter.get_by_id(SessionIdRef("session-1"))
        assert isinstance(result, SessionReference)
        assert result.session_id == SessionIdRef("session-1")
        mock_client.get.assert_awaited_once_with("/api/v1/sessions/session-1")

    async def test_get_by_id_fetches_fresh_data_on_each_call(
        self,
        adapter: SessionReaderHttpAdapter,
        mock_client: AsyncMock,
    ) -> None:
        mock_client.get = AsyncMock(
            side_effect=(
                Mock(status_code=200, json=Mock(return_value={"id": "session-1"})),
                Mock(status_code=200, json=Mock(return_value={"id": "session-2"})),
            )
        )

        first = await adapter.get_by_id(SessionIdRef("session-1"))
        second = await adapter.get_by_id(SessionIdRef("session-1"))

        assert first is not None
        assert second is not None
        assert first.session_id == SessionIdRef("session-1")
        assert second.session_id == SessionIdRef("session-2")
        assert mock_client.get.await_count == 2

    async def test_get_by_id_maps_only_required_field(
        self,
        adapter: SessionReaderHttpAdapter,
        mock_client: AsyncMock,
    ) -> None:
        response_data = {
            "id": "session-2",
        }
        mock_client.get = AsyncMock(
            return_value=Mock(status_code=200, json=Mock(return_value=response_data))
        )
        result = await adapter.get_by_id(SessionIdRef("session-2"))
        assert isinstance(result, SessionReference)
        assert result.session_id == SessionIdRef("session-2")

    async def test_raises_on_5xx(
        self,
        adapter: SessionReaderHttpAdapter,
        mock_client: AsyncMock,
    ) -> None:
        mock_client.get = AsyncMock(
            return_value=Mock(
                status_code=500, raise_for_status=Mock(side_effect=Exception("Server error"))
            )
        )
        with pytest.raises(Exception, match="Server error"):
            await adapter.get_by_id(SessionIdRef("session-1"))
