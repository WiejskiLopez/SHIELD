"""Obsługa WebSocket dla strumieni sesji — KONCEPCJA FUTURE (nieaktywna).

Status: planowany (future concept), nie podłączony produkcyjnie.
Brak rejestracji jakiejkolwiek trasy WebSocket w aplikacjach BC
(``app.websocket`` / ``add_api_websocket_route``), brak instancji tego handlera
w composition root oraz brak testów. Klasse utrzymujemy jako propozycję
pod przyszły sygnał czasu rzeczywistego (np. push eventów sesji do klienta).

Decyzja techniczna: jeżeli koncept nie zostanie wdrożony w rozsądnym
horyzoncie i stanie się martwym kodem legacy (nieużywana, nieprzetestowana
abstrakcja), NALEŻY go przebudować/uwzględnić w architekturze, a nie
utrzymywać bezczynnie. Domniemanie: aktywny WebSocket wymaga osobnego
kontraktu i middleware'a (transport dwukierunkowy, inny niż HTTP), patrz
notatki o observability w conversacji projektowej.

FIX6 (DoS hardening konceptu):
- max 100 peerów globalnie i max 10 per ``session_id`` (odrzucenie 1013),
- timeout ``receive`` 60s (zamknięcie 1011),
- limit rozmiaru wiadomości 64KB (zamknięcie 1009),
- walidacja ``session_id`` (non-empty, max 128 znaków) przed ``accept``
  (zamknięcie 4400),
- opcjonalny ``expected_token`` porównywany ``hmac.compare_digest`` na
  pierwszej wiadomości (brak/niezgodność -> zamknięcie 4401).

Publiczny eksport pakietu ``shell.platform.framework.api.ws`` jest bramkowany
flagą ``SHELL_ENABLE_WS`` — bez flagi handler pozostaje konceptem dostępnym
wyłącznie przez bezpośredni import modułu ``session_ws``.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
from typing import TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from shell.platform.application.bus.event_bus import EventBus

logger = logging.getLogger(__name__)

MAX_GLOBAL_PEERS = 100
MAX_PEERS_PER_SESSION = 10
MAX_MESSAGE_BYTES = 64 * 1024
RECEIVE_TIMEOUT_SECONDS = 60.0
MAX_SESSION_ID_LENGTH = 128

INVALID_SESSION_CLOSE_CODE = 4400
AUTH_FAILED_CLOSE_CODE = 4401
OVERLOADED_CLOSE_CODE = 1013
MESSAGE_TOO_BIG_CLOSE_CODE = 1009
RECEIVE_TIMEOUT_CLOSE_CODE = 1011


def is_valid_session_id(session_id: str) -> bool:
    """Sprawdź ``session_id`` przed ``accept`` (non-empty, max 128 znaków)."""
    if not isinstance(session_id, str):
        return False
    if not session_id or not session_id.strip():
        return False
    return len(session_id) <= MAX_SESSION_ID_LENGTH


class SessionWebSocketHandler:
    def __init__(
        self,
        event_bus: EventBus,
        *,
        receive_timeout_seconds: float = RECEIVE_TIMEOUT_SECONDS,
    ) -> None:
        self._event_bus = event_bus
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._receive_timeout_seconds = receive_timeout_seconds

    async def handle(
        self,
        websocket: WebSocket,
        session_id: str,
        expected_token: str | None = None,
    ) -> None:
        if not is_valid_session_id(session_id):
            try:
                await websocket.close(code=INVALID_SESSION_CLOSE_CODE, reason="invalid session_id")
            except Exception:
                logger.warning("websocket reject failed for invalid session_id")
            return

        async with self._lock:
            total = sum(len(peers) for peers in self._connections.values())
            per_session = len(self._connections.get(session_id, []))
            overloaded = total >= MAX_GLOBAL_PEERS or per_session >= MAX_PEERS_PER_SESSION
        if overloaded:
            try:
                await websocket.close(code=OVERLOADED_CLOSE_CODE, reason="server overloaded")
            except Exception:
                logger.warning("websocket reject failed for overloaded session %s", session_id)
            return

        await websocket.accept()

        async with self._lock:
            total = sum(len(peers) for peers in self._connections.values())
            per_session = len(self._connections.get(session_id, []))
            if total >= MAX_GLOBAL_PEERS or per_session >= MAX_PEERS_PER_SESSION:
                overloaded_after_accept = True
            else:
                self._connections.setdefault(session_id, []).append(websocket)
                overloaded_after_accept = False
        if overloaded_after_accept:
            try:
                await websocket.close(code=OVERLOADED_CLOSE_CODE, reason="server overloaded")
            except Exception:
                logger.warning("websocket reject-after-accept failed for session %s", session_id)
            return

        try:
            if expected_token is not None:
                try:
                    first = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=self._receive_timeout_seconds,
                    )
                except TimeoutError:
                    try:
                        await websocket.close(
                            code=RECEIVE_TIMEOUT_CLOSE_CODE, reason="receive timeout"
                        )
                    except Exception:
                        logger.warning("websocket timeout close failed for session %s", session_id)
                    return
                except WebSocketDisconnect:
                    return
                if len(first.encode("utf-8")) > MAX_MESSAGE_BYTES:
                    try:
                        await websocket.close(
                            code=MESSAGE_TOO_BIG_CLOSE_CODE, reason="message too big"
                        )
                    except Exception:
                        logger.warning("websocket oversize close failed for session %s", session_id)
                    return
                if not hmac.compare_digest(first.encode("utf-8"), expected_token.encode("utf-8")):
                    try:
                        await websocket.close(code=AUTH_FAILED_CLOSE_CODE, reason="unauthorized")
                    except Exception:
                        logger.warning("websocket auth close failed for session %s", session_id)
                    return
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=self._receive_timeout_seconds,
                    )
                except TimeoutError:
                    try:
                        await websocket.close(
                            code=RECEIVE_TIMEOUT_CLOSE_CODE, reason="receive timeout"
                        )
                    except Exception:
                        logger.warning("websocket timeout close failed for session %s", session_id)
                    break
                except WebSocketDisconnect:
                    break
                if len(message.encode("utf-8")) > MAX_MESSAGE_BYTES:
                    try:
                        await websocket.close(
                            code=MESSAGE_TOO_BIG_CLOSE_CODE, reason="message too big"
                        )
                    except Exception:
                        logger.warning("websocket oversize close failed for session %s", session_id)
                    break
        finally:
            async with self._lock:
                conns = self._connections.get(session_id, [])
                if websocket in conns:
                    conns.remove(websocket)
                if not self._connections.get(session_id):
                    self._connections.pop(session_id, None)

    async def broadcast(self, session_id: str, event: dict[str, object]) -> None:
        async with self._lock:
            peers = list(self._connections.get(session_id, []))
        for ws in peers:
            try:
                await ws.send_json(event)
            except Exception:
                logger.warning("websocket send failed for session %s; removing peer", session_id)
                async with self._lock:
                    conns = self._connections.get(session_id, [])
                    if ws in conns:
                        conns.remove(ws)
