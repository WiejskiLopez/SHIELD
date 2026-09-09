"""Koncept: granica port-adapter dla biblioteki sagi.

Reguła: warstwy `domain`/`application`/`process` serwisów nie importują
`saga_orchestration.infrastructure` (implementacje SQL/InMemory/worker).
Porty (`domain/ports`, handlery aplikacyjne) tak — konkret podpina wyłącznie
bootstrap/kompozycja.

Poprawnie: serwis widzi porty libki, infra libki dotyka tylko bootstrap.
"""

from __future__ import annotations

from _arch_helpers import BASE, architecture_assertion_message
from saga_topology_paths import saga_python_files


def test_service_layers_do_not_import_saga_infrastructure() -> None:
    offenders: list[str] = []
    for root in sorted(BASE.glob("*_service")):
        for layer in ("domain", "application", "process"):
            layer_root = root / layer
            if not layer_root.is_dir():
                continue
            for path in saga_python_files(layer_root):
                text = path.read_text(encoding="utf-8")
                if "saga_orchestration.infrastructure" in text:
                    offenders.append(str(path))
    assert not offenders, architecture_assertion_message(
        "test_service_layers_do_not_import_saga_infrastructure",
        "warstwy importują infra sagi (mają używać portów przez bootstrap)",
        offenders,
    )
