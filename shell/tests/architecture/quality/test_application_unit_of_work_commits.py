"""Koncept: jawny commit aplikacyjnych zapisów przez UoW.

Reguła: każdy aplikacyjny zapis przez UoW musi mieć jawny commit.
Poprawnie: funkcja z `save` lub `save_many` wywołuje `unit_of_work.commit()`.
"""

from __future__ import annotations

import ast

from _arch_helpers import BASE, architecture_failure, iter_py_files


def _application_files() -> list:
    return [
        path
        for service_root in sorted(BASE.glob("*_service"))
        for path in iter_py_files(service_root / "application")
    ]


def _has_explicit_commit(function: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "commit"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "unit_of_work"
        for node in ast.walk(function)
    )


def test_application_uow_save_sites_have_explicit_commit() -> None:
    violations: list[str] = []
    save_site_count = 0

    for path in _application_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            save_sites = [
                node
                for node in ast.walk(function)
                if isinstance(node, ast.Await)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr in {"save", "save_many"}
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id == "unit_of_work"
            ]
            if not save_sites:
                continue
            save_site_count += len(save_sites)
            if not _has_explicit_commit(function):
                violations.append(f"{path.relative_to(BASE)}:{function.lineno}:{function.name}")

    assert save_site_count, "Nie znaleziono żadnego aplikacyjnego zapisu przez unit_of_work"
    if violations:
        raise AssertionError(
            architecture_failure(
                "aplikacyjny zapis przez UnitOfWork wymaga jawnego commitu",
                "każda funkcja z unit_of_work.save/save_many zawiera unit_of_work.commit()",
                violations,
            )
        )