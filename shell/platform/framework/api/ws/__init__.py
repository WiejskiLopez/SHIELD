"""WebSocket package — koncept FUTURE, nie prod.

Publiczny eksport ``SessionWebSocketHandler`` jest dostępny wyłącznie za flagą
``SHELL_ENABLE_WS=1`` (wartości: 1/true/yes/on). Bez flagi pakiet nie
eksportuje niczego — bezpośredni import konceptu pozostaje możliwy przez
``shell.platform.framework.api.ws.session_ws`` (testy/lokalny prototyp).
"""

from __future__ import annotations

import os

__all__: list[str] = []

if os.getenv("SHELL_ENABLE_WS", "").strip().lower() in {"1", "true", "yes", "on"}:
    from shell.platform.framework.api.ws.session_ws import SessionWebSocketHandler

    __all__ = ["SessionWebSocketHandler"]
