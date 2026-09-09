"""Błąd warstwy aplikacji (ApplicationError).

Klasa bazowa dla błędów rzucanych podczas koordynacji przypadku użycia aplikacji.
"""

from __future__ import annotations


class ApplicationError(Exception):
    pass