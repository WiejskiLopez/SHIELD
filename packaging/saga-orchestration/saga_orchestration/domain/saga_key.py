from __future__ import annotations

from dataclasses import dataclass

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError


@dataclass(frozen=True, slots=True)
class SagaKey(ValueObject):
    """Klucz korelacji biznesowej: typ sagi + klucz biznesowy (np. project_id)."""

    saga_type: str
    business_key: str

    def __post_init__(self) -> None:
        if not self.saga_type or len(self.saga_type) > 128:
            raise SagaDomainError(f"invalid saga_type: {self.saga_type!r}")
        if not self.business_key or len(self.business_key) > 256:
            raise SagaDomainError(f"invalid business_key: {self.business_key!r}")
