"""Koncept: spójność ścieżek importów projektu.

Reguła: każdy import modułu projektu wskazuje istniejącą ścieżkę na dysku.
Poprawnie: importowany moduł lub pakiet istnieje w repozytorium.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from _arch_helpers import BASE, architecture_assertion_message, iter_py_files, parse_file

_PROJECT_PACKAGE = "shell"


def _module_name(path: Path) -> tuple[str, ...]:
    relative = path.relative_to(BASE).with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return (_PROJECT_PACKAGE, *parts)


def _module_exists(module_parts: tuple[str, ...]) -> bool:
    module_path = BASE.parent.joinpath(*module_parts)
    return module_path.with_suffix(".py").is_file() or module_path.is_dir()


def _absolute_import_parts(
    node: ast.Import | ast.ImportFrom, source_path: Path
) -> list[tuple[str, ...]]:
    if isinstance(node, ast.Import):
        return [tuple(alias.name.split(".")) for alias in node.names]

    if node.level == 0:
        if node.module is None:
            return []
        return [tuple(node.module.split("."))]

    current_parts = _module_name(source_path)
    package_parts = current_parts[:-1]
    parent_length = max(0, len(package_parts) - node.level + 1)
    base_parts = package_parts[:parent_length]
    module_parts = tuple(node.module.split(".")) if node.module else ()
    if module_parts:
        return [(*base_parts, *module_parts)]
    return [(*base_parts, alias.name) for alias in node.names]


def test_project_import_modules_exist_on_disk() -> None:
    violations: list[str] = []
    for path in iter_py_files(BASE):
        tree = parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            imports = _absolute_import_parts(node, path)
            for module_parts in imports:
                if not module_parts or module_parts[0] != _PROJECT_PACKAGE:
                    continue
                if not _module_exists(module_parts):
                    module_name = ".".join(module_parts)
                    violations.append(
                        f"{path.relative_to(BASE)}: import {module_name} has no matching .py file or package"
                    )

    assert not violations, architecture_assertion_message(
        "test_project_import_modules_exist_on_disk",
        "każdy import projektu musi wskazywać istniejący moduł lub pakiet",
        "Missing project import paths:\n" + "\n".join(violations),
    )
