"""Koncept: reguła architektoniczna dotycząca enterprise patterns: test all repository ports have in memory.

Reguła: test sprawdza kontrakt architektoniczny enterprise patterns: test all repository ports have in memory.

Poprawnie: kod spełnia ten kontrakt i nie zgłasza naruszeń.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

from _arch_helpers import (
    BASE,
    architecture_assertion_message,
    find_classes,
    iter_layer_files,
    iter_named_dirs,
    iter_py_files,
    parse_file,
    to_snake_case,
)


def _find_repository_ports() -> list[tuple[pathlib.Path, str]]:
    """Return (file_path, class_name) for every Protocol ending in Repository across repositories."""
    results: list[tuple[pathlib.Path, str]] = []
    for repos_dir in iter_named_dirs("domain", "repositories"):
        for py_file in iter_py_files(repos_dir):
            tree = parse_file(py_file)
            if tree is None:
                continue
            for node in find_classes(tree):
                if not node.name.endswith("Repository"):
                    continue
                if any(isinstance(base, ast.Name) and base.id == "Protocol" for base in node.bases):
                    results.append((py_file, node.name))
    return results


def test_all_repository_ports_have_in_memory() -> None:
    repos = _find_repository_ports()
    missing: list[str] = []
    for file_path, class_name in repos:
        snake = to_snake_case(class_name)
        expected_pat = f"in_memory_{snake}.py"
        candidates = [
            path for path in iter_layer_files("infrastructure") if path.name == expected_pat
        ]
        if not candidates:
            missing.append(f"{file_path.relative_to(BASE)}: {class_name}")
            continue
        implements_port = False
        required_methods = {
            method.name
            for node in find_classes(parse_file(file_path) or ast.Module(body=[], type_ignores=[]))
            if node.name == class_name
            for method in node.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        inherited_methods = {"get_by_id", "save", "delete", "exists"}
        for candidate in candidates:
            tree = parse_file(candidate)
            if tree is None:
                continue
            for node in find_classes(tree):
                if not any(
                    isinstance(base, ast.Name) and base.id == class_name for base in node.bases
                ):
                    continue
                implements_port = True
                implemented_methods = {
                    method.name
                    for method in node.body
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                missing_methods = required_methods - implemented_methods - inherited_methods
                if missing_methods:
                    missing.append(
                        f"{candidate.relative_to(BASE)}: brak metod {sorted(missing_methods)} "
                        f"z portu {class_name}"
                    )
        if not implements_port:
            missing.append(
                f"{file_path.relative_to(BASE)}: {expected_pat} nie dziedziczy po {class_name}"
            )
    assert not missing, architecture_assertion_message(
        "reguła testowana przez test_all_repository_ports_have_in_memory",
        "warunek zapisany w asercji musi być spełniony",
        "Repository ports must have a corresponding InMemory implementation:\n"
        + "\n".join(missing),
    )
