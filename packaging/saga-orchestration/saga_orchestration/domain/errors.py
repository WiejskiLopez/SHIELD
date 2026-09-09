from __future__ import annotations


class SagaDomainError(Exception):
    """Baza błędów domenowych sagi."""


class SagaGuardError(SagaDomainError):
    """Naruszenie invariantu przejścia stanu (fail-fast, przed mutacją)."""


class SagaVersionConflictError(SagaDomainError):
    """Optymistyczny konflikt zapisu: wiersz zmienił się między load a store."""
