"""Koncept: wiring sagi wyłącznie przez install_saga.

Reguła: żaden kontener DI (`shell/*/bootstrap/*/container/*.py`) nie podpina
implementacji libki wprost (`SqlSagaRepository`, `SqlSagaTimeoutRepository`,
`SagaTimeoutProcessor`, `build_command_delivery_dispatcher`) — wszystko idzie
przez `install_saga` (SAGA.MD Krok 7).

Poprawnie: kontenery widzą tylko `install_saga`, nigdy klasy implementacyjne.
"""

from __future__ import annotations

from _arch_helpers import architecture_assertion_message
from saga_topology_paths import saga_container_texts

_FORBIDDEN_DIRECT = (
    "SqlSagaRepository",
    "SqlSagaTimeoutRepository",
    "SagaTimeoutProcessor",
    "build_command_delivery_dispatcher",
)


def test_saga_wiring_goes_through_install_saga() -> None:
    direct: list[str] = []
    for service, text in saga_container_texts().items():
        hits = [symbol for symbol in _FORBIDDEN_DIRECT if symbol in text]
        if hits:
            direct.append(f"{service}: {sorted(hits)}")
    assert not direct, architecture_assertion_message(
        "test_saga_wiring_goes_through_install_saga",
        "kontenery spinają sagę wyłącznie przez install_saga (SAGA.MD Krok 7)",
        direct,
    )
