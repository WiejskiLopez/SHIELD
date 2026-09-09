"""Koncept: serwisy bez sag nie mają schematu sagi.

Reguła: serwisy inne niż właściciele (project, scheduling) nie mają migracji
sagowych w `migrations/versions` ani `SAGA_MODELS` / `build_saga_models`
w modelach (SAGA.MD Krok 7, RFC-07).

Poprawnie: serwis bez własnej sagi nie ma tabel sagi.
"""

from __future__ import annotations

from _arch_helpers import BASE, architecture_assertion_message
from saga_topology_paths import SAGA_OWNERS


def test_saga_adoption_non_owners_have_no_saga_schema() -> None:
    offenders: list[str] = []
    services = sorted(path.name for path in BASE.glob("*_service") if path.is_dir())
    for service in services:
        if service in SAGA_OWNERS:
            continue
        versions = BASE / service / "migrations" / "versions"
        if versions.is_dir():
            saga_files = sorted(
                path.name for path in versions.glob("*.py") if "saga" in path.name.lower()
            )
            if saga_files:
                offenders.append(f"{service}/migrations/versions: {saga_files}")
        for base_path in sorted((BASE / service).rglob("models/base.py")):
            text = base_path.read_text(encoding="utf-8")
            if "SAGA_MODELS" in text or "build_saga_models" in text:
                offenders.append(f"{base_path.relative_to(BASE).as_posix()}: modele sagi")
    assert not offenders, architecture_assertion_message(
        "test_saga_adoption_non_owners_have_no_saga_schema",
        "serwisy bez sag nie mają schematu sagi (RFC-07)",
        offenders,
    )
