"""Błędy walidacji komend na granicy warstwy aplikacji."""

from __future__ import annotations

from shell.platform.application.exceptions.application_error import ApplicationError


class CommandValidationError(ApplicationError):
    """Błąd bazowy dla niepoprawnego wejścia komendy na granicy aplikacji."""


class RequiredCommandFieldError(CommandValidationError):
    """Rzucony, gdy wymagane pole komendy jest puste lub brakuje."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(f"{field_name} cannot be empty")


class InvalidCommandFieldError(CommandValidationError):
    """Rzucony, gdy pole komendy ma niepoprawną wartość."""

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name}: {reason}")