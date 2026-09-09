"""Koncept: pełny pakiet sagi u właścicieli typów.

Reguła: serwisy-właściciele (project, scheduling) wystawiają `install_saga`
+ `saga_timeout_worker_factory` + `SagaTimeoutReadinessProbe` + `SAGA_MODELS`
— dokładnie te dwa serwisy i żaden inny (SAGA.MD Krok 7, RFC-07).

Poprawnie: drugi serwis powtarza wiring właściciela 1:1.
"""

from __future__ import annotations

from _arch_helpers import architecture_assertion_message
from saga_topology_paths import SAGA_OWNERS, saga_container_texts

_OWNER_REQUIRED = (
    "install_saga",
    "saga_timeout_worker_factory",
    "SagaTimeoutReadinessProbe",
    "SAGA_MODELS",
)


def test_saga_wiring_owners_expose_full_bundle() -> None:
    containers = saga_container_texts()
    offenders: list[str] = []
    wired = sorted(service for service, text in containers.items() if "install_saga" in text)
    if wired != sorted(SAGA_OWNERS):
        offenders.append(f"install_saga w: {wired}, oczekiwano: {sorted(SAGA_OWNERS)}")
    for service in sorted(SAGA_OWNERS):
        missing = [
            symbol for symbol in _OWNER_REQUIRED if symbol not in containers.get(service, "")
        ]
        if missing:
            offenders.append(f"{service}: brak {sorted(missing)}")
    assert not offenders, architecture_assertion_message(
        "test_saga_wiring_owners_expose_full_bundle",
        "właściciele typów wystawiają pełny pakiet sagi (wiring + worker + probe)",
        offenders,
    )
