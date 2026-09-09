"""Koncept: kompletność transactional Unit of Work w bounded contexts.

Reguła: każdy bounded context obsługujący zapisy musi mieć SQL i InMemory UoW.

Poprawnie: kod spełnia ten kontrakt i nie zgłasza naruszeń.
"""

from __future__ import annotations

import ast

from _arch_helpers import BASE, iter_py_files, parse_file

_BOUNDED_CONTEXTS = (
    "definition",
    "execution",
    "ingestion",
    "project",
    "scheduling",
    "session",
    "user",
)


def _has_class_extending(service_root: object, base_name: str) -> bool:
    found = False
    for py_file in iter_py_files(service_root):
        tree = parse_file(py_file)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if any(
                isinstance(base, ast.Name) and base.id == base_name for base in node.bases
            ):
                found = True
    return found


def test_each_bounded_context_has_sql_and_in_memory_uow() -> None:
    violations: list[str] = []
    for bounded_context in _BOUNDED_CONTEXTS:
        service_root = BASE / f"{bounded_context}_service"
        if not _has_class_extending(service_root, "InMemoryUnitOfWorkBase"):
            violations.append(f"{bounded_context}: brak InMemoryUnitOfWorkBase")
        if not _has_class_extending(service_root, "SqlAlchemyUnitOfWorkBase"):
            violations.append(f"{bounded_context}: brak SqlAlchemyUnitOfWorkBase")

    assert not violations, "Niekompletna para UoW:\n" + "\n".join(violations)