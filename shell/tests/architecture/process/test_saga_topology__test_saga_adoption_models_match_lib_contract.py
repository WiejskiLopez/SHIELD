"""Koncept: modele sagi zgodne z DDL libki.

Reguła: `SAGA_MODELS` każdego właściciela (project, scheduling) ma tabele
`saga_instance` / `saga_timeout` / `saga_processed_delivery` z kolumnami
kontraktu libki 1:1 (RFC-02/03) — jedyne źródło DDL to `saga_schema.py`
(SAGA.MD Krok 5/8, RFC-06).

Poprawnie: serwis adoptuje DDL, nie definiuje własnego.
"""

from __future__ import annotations

from importlib import import_module

from _arch_helpers import architecture_assertion_message
from saga_topology_paths import EXPECTED_SAGA_COLUMNS, SAGA_OWNER_BASE_MODULES, SAGA_OWNERS


def test_saga_adoption_models_match_lib_contract() -> None:
    offenders: list[str] = []
    for service in sorted(SAGA_OWNERS):
        models = import_module(SAGA_OWNER_BASE_MODULES[service]).SAGA_MODELS
        for attr, table in (
            ("instance", "saga_instance"),
            ("timeout", "saga_timeout"),
            ("delivery", "saga_processed_delivery"),
        ):
            model = getattr(models, attr)
            actual = frozenset(model.__table__.columns.keys())
            expected = EXPECTED_SAGA_COLUMNS[table]
            if actual != expected:
                offenders.append(
                    f"{service}.{table}: kolumny {sorted(actual)} != {sorted(expected)}"
                )
            if model.__table__.name != table:
                offenders.append(f"{service}: __tablename__ {model.__table__.name!r} != {table!r}")
    assert not offenders, architecture_assertion_message(
        "test_saga_adoption_models_match_lib_contract",
        "modele SAGA_MODELS właścicieli zgodne z kontraktem DDL libki",
        offenders,
    )
