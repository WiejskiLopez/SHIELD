"""Koncept: serwisy bez sag nie dotykają sagi.

Reguła: kontenery serwisów innych niż właściciele (project, scheduling) nie
zawierają `saga_orchestration`, `install_saga`, `SAGA_MODELS` ani workerów
timeoutów (SAGA.MD Krok 7, RFC-07).

Poprawnie: serwis bez własnej sagi nie robi NIC z tej listy.
"""

from __future__ import annotations

from _arch_helpers import architecture_assertion_message
from saga_topology_paths import SAGA_OWNERS, saga_container_texts

_NON_OWNER_FORBIDDEN = (
    "saga_orchestration",
    "install_saga",
    "SAGA_MODELS",
    "saga_timeout_worker",
)


def test_saga_wiring_non_owners_stay_clean() -> None:
    offenders: list[str] = []
    for service, text in saga_container_texts().items():
        if service in SAGA_OWNERS:
            continue
        hits = [symbol for symbol in _NON_OWNER_FORBIDDEN if symbol in text]
        if hits:
            offenders.append(f"{service}: {sorted(hits)}")
    assert not offenders, architecture_assertion_message(
        "test_saga_wiring_non_owners_stay_clean",
        "serwisy bez sag nie dotykają saga_orchestration (RFC-07)",
        offenders,
    )
