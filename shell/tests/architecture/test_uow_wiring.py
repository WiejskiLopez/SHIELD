"""Koncept: wiring SQL UnitOfWork do kontenerów DI (FIX9 pkt 21+22).

Reguła: każda klasa *UnitOfWork w shell/*_service/infrastructure/**/persistence/sql/unit_of_work.py
musi być importowana w bootstrap/*/container/*_core_container.py.

Poprawnie: UoW jest używany przez handlery przez unit_of_work_factory w kontenerze BC.
"""

from __future__ import annotations

import ast

from _arch_helpers import (
    BASE,
    architecture_assertion_message,
    parse_file,
)

# Allow-lista martwych UoW (decyzja pkt26 osobno — NIE kasować w FIX9).
# Deterministyczna zamiast xfail: test jest zielony tylko gdy unwired == MARTWE.
MARTWE: frozenset[str] = frozenset(
    {
        # definition (4): wiring ma tylko node_definition; reszta bez handlerów w kontenerze.
        "definition_service/infrastructure/definition/graph_definition/persistence/sql/unit_of_work.py",
        "definition_service/infrastructure/definition/graph_definition_embedding/persistence/sql/unit_of_work.py",
        "definition_service/infrastructure/definition/node_link_definition/persistence/sql/unit_of_work.py",
        "definition_service/infrastructure/definition/runner_config/persistence/sql/unit_of_work.py",
        # execution (10): wiring ma workflow/task/node/edge/edge_link; reszta *_state/*_session/* bez handlerów.
        "execution_service/infrastructure/execution/graph_execution/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/graph_execution_state/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/node_execution_state/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/node_link_execution/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/session_execution/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/session_execution_state/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/task_execution_state/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/user_execution/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/user_execution_state/persistence/sql/unit_of_work.py",
        "execution_service/infrastructure/execution/workflow_state/persistence/sql/unit_of_work.py",
        # project (2): wiring ma tylko project; project_skill/project_state bez handlerów.
        "project_service/infrastructure/project/project_skill/persistence/sql/unit_of_work.py",
        "project_service/infrastructure/project/project_state/persistence/sql/unit_of_work.py",
        # user (2): wiring ma tylko user (User+AuthSession, pkt21); skill/state bez handlerów.
        "user_service/infrastructure/user/user_skill/persistence/sql/unit_of_work.py",
        "user_service/infrastructure/user/user_state/persistence/sql/unit_of_work.py",
    }
)


def test_uow_wiring() -> None:
    uow_files = sorted(BASE.glob("*_service/infrastructure/**/persistence/sql/unit_of_work.py"))
    containers = sorted(BASE.glob("*_service/bootstrap/*/container/*_core_container.py"))
    container_texts = [path.read_text(encoding="utf-8") for path in containers]

    unwired: list[str] = []
    unwired_detail: list[str] = []
    for uow_file in uow_files:
        # shell/tests/** nie zawiera infrastructure/**/persistence/sql/unit_of_work.py — brak akcji.
        rel = uow_file.relative_to(BASE).as_posix()
        tree = parse_file(uow_file)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not node.name.endswith("UnitOfWork"):
                continue
            # Ingestion inline UoW (IngestionUnitOfWork w bootstrap) nie jest plikiem
            # infrastructure — z definicji pomijany, bo skanujemy tylko infrastructure/.
            if not any(node.name in text for text in container_texts):
                unwired.append(rel)
                unwired_detail.append(f"{rel}:: class {node.name}")

    unwired_set = set(unwired)
    unexpected = sorted(unwired_set - MARTWE)
    stale = sorted(MARTWE - unwired_set)
    assert not unexpected and not stale, architecture_assertion_message(
        "reguła testowana przez test_uow_wiring",
        "każdy SQL UoW jest wpięty do *_core_container.py albo widnieje w MARTWE (pkt26)",
        "Niewpięte UoW poza allow-listą:\n"
        + ("\n".join(unexpected) if unexpected else "(brak)")
        + "\nStale wpisy MARTWE (już wpięte — usuń z allow-listy):\n"
        + ("\n".join(stale) if stale else "(brak)")
        + "\nWszystkie niewpięte (detail):\n"
        + ("\n".join(sorted(unwired_detail)) if unwired_detail else "(brak)")
        + "\nJak naprawić: wpnij UoW do kontenera BC albo dopisz do MARTWE z decyzją pkt26.",
    )
