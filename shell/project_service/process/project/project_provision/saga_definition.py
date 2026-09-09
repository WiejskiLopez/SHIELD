"""Deklaracja sagi project_provision na nowym modelu (SAGA.MD Krok 4).

Żyje OBOK pilota (`manager.py` + `steps.py` nietknięte). Różnice względem pilota
są celowe: timeout wyniku, retry z backoff (pilot: max_attempts=1, brak timeoutu).
"""

from __future__ import annotations

from datetime import timedelta

from saga_orchestration.domain.step import StepDefinition, StepRegistry
from saga_orchestration.domain.step_name import StepName

SAGA_TYPE = "project_provision"

PROJECT_PROVISION_STEPS_V2 = StepRegistry(
    steps=(
        StepDefinition(
            name=StepName("provision_workspace"),
            target_service="project",
            compensation_step=StepName("release_workspace"),
            timeout=timedelta(minutes=5),
            max_attempts=2,
            backoff=timedelta(seconds=30),
        ),
    )
)
