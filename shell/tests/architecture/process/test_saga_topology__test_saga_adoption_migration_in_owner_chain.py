"""Koncept: deterministyczna adopcja schematu sagi w łańcuchu właściciela.

Reguła: każdy właściciel (project, scheduling) ma dokładnie jedną migrację
adopcyjną `*_saga_schema.py` wołającą `upgrade_saga_schema` /
`downgrade_saga_schema` na `SAGA_MODELS`, liniowo wpiętą w łańcuch —
adopcja to head (SAGA.MD Krok 5/8, RFC-06).

Poprawnie: migracja adoptuje, nie zgaduje stanu (bez IF NOT EXISTS).
"""

from __future__ import annotations

from _arch_helpers import BASE, architecture_assertion_message
from saga_topology_paths import SAGA_OWNERS, saga_module_constant


def test_saga_adoption_migration_in_owner_chain() -> None:
    offenders: list[str] = []
    for service in sorted(SAGA_OWNERS):
        versions = BASE / service / "migrations" / "versions"
        adoptions = sorted(versions.glob("*_saga_schema.py"))
        if len(adoptions) != 1:
            offenders.append(f"{service}: adopcji {len(adoptions)}, oczekiwano 1")
            continue
        adoption = adoptions[0]
        text = adoption.read_text(encoding="utf-8")
        for symbol in ("upgrade_saga_schema", "downgrade_saga_schema", "SAGA_MODELS"):
            if symbol not in text:
                offenders.append(f"{service}/{adoption.name}: brak {symbol}")
        revisions: dict[str, str | None] = {}
        for path in versions.glob("*.py"):
            if path.name == "__init__.py":
                continue
            revision = saga_module_constant(path, "revision")
            if revision is not None:
                revisions[revision] = saga_module_constant(path, "down_revision")
        adoption_revision = saga_module_constant(adoption, "revision")
        if adoption_revision is None:
            offenders.append(f"{service}/{adoption.name}: brak revision")
            continue
        down_targets = {down for down in revisions.values() if down is not None}
        heads = [revision for revision in revisions if revision not in down_targets]
        if heads != [adoption_revision]:
            offenders.append(f"{service}: head {heads}, oczekiwano [{adoption_revision}]")
    assert not offenders, architecture_assertion_message(
        "test_saga_adoption_migration_in_owner_chain",
        "adopcja sagi deterministyczna i liniowa, saga to head łańcucha",
        offenders,
    )
