"""Koncept: repository.delete is hard-delete.

Reguła: soft-delete należy do agregatu i przechodzi przez save(). Metoda
repository.delete() fizycznie usuwa rekord z SQL albo InMemory.

Poprawnie: każde repozytorium ma jawny hard-delete.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from _arch_helpers import BASE, architecture_assertion_message, iter_py_files, parse_file

if TYPE_CHECKING:
    from pathlib import Path


def _repository_files() -> list[Path]:
    return [
        path
        for path in iter_py_files(BASE)
        if "infrastructure" in path.parts
        and "persistence" in path.parts
        and ("repositories" in path.parts or path.name.startswith("in_memory_"))
    ]


def _delete_methods(tree: ast.Module) -> list[ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "delete"
    ]


def _has_hard_delete(method: ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(method):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in {"pop", "remove"}:
            return True
        if node.func.attr == "delete":
            if isinstance(node.func.value, ast.Name):
                return node.func.value.id in {"session", "self"}
            if isinstance(node.func.value, ast.Attribute):
                return node.func.value.attr in {"session", "_session"}
    return False


def test_repository_delete_is_hard_delete() -> None:
    violations: list[str] = []
    for path in _repository_files():
        tree = parse_file(path)
        if tree is None:
            continue
        for method in _delete_methods(tree):
            if not _has_hard_delete(method):
                violations.append(f"{path.relative_to(BASE)}:{method.lineno}")

    assert not violations, architecture_assertion_message(
        "repository hard-delete contract",
        "repository.delete() physically removes the record; aggregate soft-delete uses save()",
        "\n".join(violations),
    )
