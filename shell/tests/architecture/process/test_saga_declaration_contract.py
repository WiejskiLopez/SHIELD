"""Koncept: kontrakt deklaracji sag bounded contextów.

Reguła: saga ma kroki, kompensację, timeout i retry, a biblioteka odrzuca złe wartości.
Poprawnie: deklaracje sag są wykonywalne i odporne na błędną konfigurację.
"""

from datetime import timedelta

import pytest
from saga_orchestration.domain.errors import SagaDomainError
from saga_orchestration.domain.step import StepDefinition
from saga_orchestration.domain.step_name import StepName

from shell.project_service.process.project.project_provision.saga_definition import (
    PROJECT_PROVISION_STEPS_V2,
)
from shell.scheduling_service.process.scheduling.scheduler_provision.saga_definition import (
    SCHEDULER_PROVISION_STEPS,
)


@pytest.mark.parametrize(
    "registry",
    (PROJECT_PROVISION_STEPS_V2, SCHEDULER_PROVISION_STEPS),
)
def _check_owned_sagas_declare_retry_timeout_and_compensation(registry: object) -> None:
    steps = registry.steps  # type: ignore[attr-defined]

    assert steps
    for step in steps:
        assert step.name.value
        assert step.target_service
        assert step.compensation_step is not None
        assert step.timeout is not None and step.timeout > timedelta(0)
        assert step.max_attempts >= 1


def _check_step_definition_rejects_invalid_retry_and_timeout_configuration() -> None:
    with pytest.raises(SagaDomainError):
        StepDefinition(
            name=StepName("provision"),
            target_service="project",
            compensation_step=StepName("release"),
            timeout=timedelta(0),
        )

    with pytest.raises(SagaDomainError):
        StepDefinition(
            name=StepName("provision"),
            target_service="project",
            compensation_step=StepName("release"),
            max_attempts=0,
        )


def test_saga_declaration_contract() -> None:
    for registry in (PROJECT_PROVISION_STEPS_V2, SCHEDULER_PROVISION_STEPS):
        _check_owned_sagas_declare_retry_timeout_and_compensation(registry)
    _check_step_definition_rejects_invalid_retry_and_timeout_configuration()
