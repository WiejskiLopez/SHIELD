"""Koncept: brak współdzielonego cache odczytów między BC.

Reguła: usunięty cache nie może wrócić do kodu produkcyjnego.
Poprawnie: odczyty korzystają z aktualnego adaptera źródłowego.
"""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
_REMOVED_SYMBOL = "Async" + "ReadThrough" + "Cache"
_EXCLUDED_PARTS = {"tests", "__pycache__", ".venv", "build", "dist"}


def _production_python_files() -> list[Path]:
    return [
        path
        for path in BASE.rglob("*.py")
        if not _EXCLUDED_PARTS.intersection(path.parts)
    ]


def test_removed_read_cache_has_no_production_artifact_or_usage() -> None:
    paths = _production_python_files()

    assert not any(path.name == "read_cache.py" for path in paths)
    usages = [
        path
        for path in paths
        if _REMOVED_SYMBOL in path.read_text(encoding="utf-8")
    ]
    assert usages == []