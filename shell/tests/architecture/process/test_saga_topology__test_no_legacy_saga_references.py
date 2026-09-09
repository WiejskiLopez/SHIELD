"""Koncept: brak pozostałości po pilocie sagi.

Reguła: w kodzie produkcyjnym i testach nie występują: stare drzewo libki
(`process.saga`, `infrastructure.process.saga`), migracje pilota
(`platform_0008/0009`, `capability_adopted`), stara klasa `SagaTimedOut`
(bez sufiksu Event), manager pilota ani stara fabryka modeli.

Poprawnie: po przebudowie (SAGA.MD Krok 6) legacy nie istnieje nigdzie.
"""

from __future__ import annotations

import re

from _arch_helpers import BASE, architecture_assertion_message
from saga_topology_paths import SAGA, saga_python_files

_LITERAL_PATTERNS = (
    "saga_orchestration.process.saga",
    "saga_orchestration.infrastructure.process.saga",
    "platform_0008_saga_instance",
    "platform_0009_saga_timeout",
    "capability_adopted",
    "ProjectProvisionSagaManager",
    "build_project_provision_manager_factory",
    "build_saga_delivery_models",
)
_WORD_PATTERNS = (r"\bSagaTimedOut\b(?!Event)",)


def test_no_legacy_saga_references() -> None:
    offenders: list[str] = []
    scan_roots = [BASE, SAGA, BASE.parent / "packaging" / "saga-orchestration"]
    for root in scan_roots:
        for path in saga_python_files(root):
            if path.name in {"saga_topology_paths.py"} or path.name.startswith(
                "test_saga_topology__"
            ):
                continue
            text = path.read_text(encoding="utf-8")
            hits = [pattern for pattern in _LITERAL_PATTERNS if pattern in text]
            hits.extend(
                pattern for pattern in _WORD_PATTERNS if re.search(pattern, text) is not None
            )
            if hits:
                offenders.append(f"{path}: {sorted(set(hits))}")
    assert not offenders, architecture_assertion_message(
        "test_no_legacy_saga_references",
        "pozostałości legacy sagi (stare drzewo/migracje/manager)",
        offenders,
    )
