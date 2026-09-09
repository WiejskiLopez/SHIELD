"""Błędy kontraktów warstwy aplikacji."""

from __future__ import annotations

from shell.platform.application.exceptions.application_error import ApplicationError


class ApplicationContractError(ApplicationError):
    """Błąd bazowy dla niepoprawnych rejestracji i kontraktów warstwy aplikacji."""


class CommandHandlerRegistrationError(ApplicationContractError):
    """Rzucony, gdy komenda ma już zarejestrowany handler."""


class QueryHandlerRegistrationError(ApplicationContractError):
    """Rzucony, gdy zapytanie ma już zarejestrowany handler."""


class CommandHandlerNotFoundError(ApplicationContractError):
    """Rzucony, gdy dyspozytowana komenda nie ma zarejestrowanego handlera."""


class QueryHandlerNotFoundError(ApplicationContractError):
    """Rzucony, gdy dyspozytowane zapytanie nie ma zarejestrowanego handlera."""


class ContractCatalogCoverageError(ApplicationContractError, ValueError):
    """Rzucony, gdy kontrakt aplikacji brakuje w katalogu."""