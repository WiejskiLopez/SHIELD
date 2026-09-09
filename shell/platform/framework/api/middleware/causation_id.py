"""Causation-ID middleware for HTTP request context propagation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shell.platform.application.context import (
    get_causation_id,
    reset_causation_id,
    set_causation_id,
)

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CausationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        causation_id = headers.get(b"x-causation-id", b"").decode()
        if not _is_valid_trace_id(causation_id):
            causation_id = ""
        token = set_causation_id(causation_id)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and get_causation_id():
                message["headers"] = list(message.get("headers", [])) + [
                    (b"X-Causation-ID", get_causation_id().encode())
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_causation_id(token)


def _is_valid_trace_id(value: str) -> bool:
    return bool(value) and len(value) <= 128 and all(char.isprintable() for char in value)
