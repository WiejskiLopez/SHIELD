from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import WebSocketDisconnect

from shell.platform.application.bus.event_bus import EventBus
from shell.platform.framework.api.ws.session_ws import (
    MAX_GLOBAL_PEERS,
    MAX_MESSAGE_BYTES,
    MAX_PEERS_PER_SESSION,
    SessionWebSocketHandler,
    is_valid_session_id,
)


class FakeWebSocket:
    """Minimalny dublet WebSocket (duck-typing dla SessionWebSocketHandler)."""

    def __init__(
        self,
        messages: list[str] | None = None,
        *,
        hang: bool = False,
        fail_send: bool = False,
    ) -> None:
        self.accepted = False
        self.closed_code: int | None = None
        self.closed_reason: str | None = None
        self.sent: list[Any] = []
        self._messages = list(messages or [])
        self._hang = hang
        self._fail_send = fail_send

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.closed_code = code
        self.closed_reason = reason

    async def receive_text(self) -> str:
        if self._hang:
            await asyncio.sleep(10)
            return ""
        if self._messages:
            return self._messages.pop(0)
        raise WebSocketDisconnect

    async def send_json(self, data: Any) -> None:
        if self._fail_send:
            raise RuntimeError("send failed")
        self.sent.append(data)


def _handler(timeout: float = 60.0) -> SessionWebSocketHandler:
    return SessionWebSocketHandler(EventBus(), receive_timeout_seconds=timeout)


def test_limits_constants() -> None:
    assert MAX_GLOBAL_PEERS == 100
    assert MAX_PEERS_PER_SESSION == 10
    assert MAX_MESSAGE_BYTES == 64 * 1024


def test_session_id_validation() -> None:
    assert is_valid_session_id("abc") is True
    assert is_valid_session_id("") is False
    assert is_valid_session_id("   ") is False
    assert is_valid_session_id("x" * 128) is True
    assert is_valid_session_id("x" * 129) is False


@pytest.mark.asyncio
async def test_invalid_session_id_rejected_before_accept() -> None:
    handler = _handler()
    for bad in ("", "x" * 129):
        fake = FakeWebSocket()
        await handler.handle(fake, bad)  # type: ignore[arg-type]
        assert fake.accepted is False
        assert fake.closed_code == 4400


@pytest.mark.asyncio
async def test_per_session_limit_rejects_with_1013() -> None:
    handler = _handler()
    handler._connections["s1"] = [FakeWebSocket() for _ in range(MAX_PEERS_PER_SESSION)]  # type: ignore[assignment]
    fake = FakeWebSocket()
    await handler.handle(fake, "s1")  # type: ignore[arg-type]
    assert fake.accepted is False
    assert fake.closed_code == 1013


@pytest.mark.asyncio
async def test_global_limit_rejects_with_1013() -> None:
    handler = _handler()
    for index in range(MAX_GLOBAL_PEERS):
        handler._connections[f"s-{index}"] = [FakeWebSocket()]  # type: ignore[assignment]
    fake = FakeWebSocket()
    await handler.handle(fake, "new-session")  # type: ignore[arg-type]
    assert fake.accepted is False
    assert fake.closed_code == 1013


@pytest.mark.asyncio
async def test_disconnect_evicts_peer() -> None:
    handler = _handler()
    fake = FakeWebSocket(messages=["hello"])
    await handler.handle(fake, "s1")  # type: ignore[arg-type]
    assert fake.accepted is True
    assert handler._connections.get("s1") in (None, [])


@pytest.mark.asyncio
async def test_oversize_message_closes_with_1009_and_evicts() -> None:
    handler = _handler()
    big = "x" * (MAX_MESSAGE_BYTES + 1)
    fake = FakeWebSocket(messages=[big])
    await handler.handle(fake, "s1")  # type: ignore[arg-type]
    assert fake.accepted is True
    assert fake.closed_code == 1009
    assert handler._connections.get("s1") in (None, [])


@pytest.mark.asyncio
async def test_auth_mismatch_closes_with_4401() -> None:
    handler = _handler()
    fake = FakeWebSocket(messages=["wrong-token"])
    await handler.handle(fake, "s1", expected_token="secret")  # type: ignore[arg-type]  # noqa: S106 -- test-only fixture token, not a production secret
    assert fake.accepted is True
    assert fake.closed_code == 4401
    assert handler._connections.get("s1") in (None, [])


@pytest.mark.asyncio
async def test_auth_match_allows_loop_then_evicts_on_disconnect() -> None:
    handler = _handler()
    fake = FakeWebSocket(messages=["secret"])
    await handler.handle(fake, "s1", expected_token="secret")  # type: ignore[arg-type]  # noqa: S106 -- test-only fixture token, not a production secret
    assert fake.accepted is True
    assert fake.closed_code is None
    assert handler._connections.get("s1") in (None, [])


@pytest.mark.asyncio
async def test_receive_timeout_closes_connection() -> None:
    handler = _handler(timeout=0.05)
    fake = FakeWebSocket(hang=True)
    await handler.handle(fake, "s1")  # type: ignore[arg-type]
    assert fake.accepted is True
    assert fake.closed_code == 1011
    assert handler._connections.get("s1") in (None, [])


@pytest.mark.asyncio
async def test_broadcast_evicts_failed_peer() -> None:
    handler = _handler()
    good = FakeWebSocket()
    bad = FakeWebSocket(fail_send=True)
    handler._connections["s1"] = [good, bad]  # type: ignore[assignment]
    await handler.broadcast("s1", {"type": "ping"})
    assert good.sent == [{"type": "ping"}]
    assert handler._connections["s1"] == [good]
