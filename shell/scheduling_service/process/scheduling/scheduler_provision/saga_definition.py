"""Deklaracja sagi scheduler_provision na modelu saga-orchestration (SAGA.MD Krok 7)."""

from __future__ import annotations

from datetime import timedelta

from saga_orchestration.domain.step import StepDefinition, StepRegistry
from saga_orchestration.domain.step_name import StepName

SAGA_TYPE = "scheduler_provision"

SCHEDULER_PROVISION_STEPS = StepRegistry(
    steps=(
        StepDefinition(
            name=StepName("provision_schedule"),
            target_service="scheduling",
            compensation_step=StepName("release_schedule"),
            timeout=timedelta(minutes=5),
            max_attempts=2,
            backoff=timedelta(seconds=30),
        ),
    )
)
