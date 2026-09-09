"""Koncept: poprawna składnia funkcji asynchronicznych Pythona.

Reguła: kod produkcyjny Pythona nie może używać składni JavaScript.
Poprawnie: funkcje asynchroniczne są deklarowane przez `async def`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from _arch_helpers import BASE, architecture_failure

if TYPE_CHECKING:
    from pathlib import Path

_EXCLUDED_PARTS = {"tests", "__pycache__", ".venv", "venv"}
_INVALID_DECLARATION = "async " + "function"


def _production_python_files() -> list[Path]:
    return [
        path
        for path in BASE.rglob("*.py")
        if not any(part in _EXCLUDED_PARTS for part in path.parts)
    ]


def test_production_python_does_not_use_javascript_async_function_syntax() -> None:
    violations: list[str] = []

    for path in _production_python_files():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _INVALID_DECLARATION in line:
                violations.append(f"{path.relative_to(BASE)}:{line_number}: {line.strip()}")

    if violations:
        raise AssertionError(
            architecture_failure(
                "kod produkcyjny Pythona nie może używać składni JavaScript",
                "funkcje asynchroniczne są deklarowane przez async def",
                violations,
            )
        )