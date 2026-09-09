from __future__ import annotations

from typing import TypeAlias

JsonValue: TypeAlias = "str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]"
"""JSON-owy payload komendy: stringi, liczby, bool, None i zagnieżdżenia.
Celowo NIE `dict[str, str]` — komendy niosą m.in. bool, liczby i obiekty."""
