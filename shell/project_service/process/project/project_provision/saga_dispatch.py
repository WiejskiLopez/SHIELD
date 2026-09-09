"""Mapowanie kroków project_provision na kontrakty wire (SAGA.MD Krok 4+)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.application.step_dispatch import StepDispatch, StepDispatchResolver
from saga_orchestration.domain.step_name import StepName

if TYPE_CHECKING:
    from saga_orchestration.domain.saga_key import SagaKey
    from saga_orchestration.domain.saga_payload import SagaPayload

PROVISION_STEP = StepName("provision_workspace")
RELEASE_STEP = StepName("release_workspace")


class ProjectProvisionDispatchResolver(StepDispatchResolver):
    """Krok -> kontrakt z command_contracts. Flaga fail z payloadu sagi."""

    def for_step(
        self, key: SagaKey, payload: SagaPayload, step: StepName, attempt: int
    ) -> StepDispatch:
        if step == RELEASE_STEP:
            return StepDispatch(
                contract_type="project.project_provision.release_workspace",
                destination_service="project",
                payload={"project_id": key.business_key, "attempt": attempt},
                aggregate_id=key.business_key,
            )
        if step == PROVISION_STEP:
            raw_fail = payload.data["fail"]
            if not isinstance(raw_fail, bool):
                raise ValueError(f"saga payload 'fail' musi być bool, jest {raw_fail!r}")
            return StepDispatch(
                contract_type="project.project_provision.provision_workspace",
                destination_service="project",
                payload={
                    "project_id": key.business_key,
                    "fail": raw_fail,
                    "attempt": attempt,
                },
                aggregate_id=key.business_key,
            )
        raise ValueError(f"brak mapowania dispatch dla kroku {step.value!r}")
