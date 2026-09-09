from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from saga_orchestration.domain.base import ValueObject
from saga_orchestration.domain.errors import SagaDomainError

if TYPE_CHECKING:
    from saga_orchestration.domain.json_value import JsonValue
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.saga_payload import SagaPayload
    from saga_orchestration.domain.step_name import StepName


@dataclass(frozen=True, slots=True)
class StepDispatch(ValueObject):
    """Kontrakt kroku do wysłania: dokąd, jakim typem, z jakim payloadem."""

    contract_type: str
    destination_service: str
    payload: dict[str, JsonValue]
    aggregate_id: str

    def __post_init__(self) -> None:
        if not self.contract_type:
            raise SagaDomainError("dispatch contract_type jest wymagany")
        if not self.destination_service:
            raise SagaDomainError("dispatch destination_service jest wymagany")
        if not self.aggregate_id:
            raise SagaDomainError("dispatch aggregate_id jest wymagany")


class StepDispatchResolver(Protocol):
    """Serwis wie, jak krok zamienić w komendę. Czyste mapowanie, zero I/O.

    Klucz `command_id` w zwracanym payloadzie jest IGNOROWANY — tożsamość komendy
    stempluje saga (determinystyczne `saga_id:krok:próba`, jedyne źródło prawdy
    dla dedupu w inbox).
    """

    def for_step(
        self, key: SagaKey, payload: SagaPayload, step: StepName, attempt: int
    ) -> StepDispatch:
        """Specyfikacja wysyłki. Dane scenariusza czyta z payloadu sagi."""
