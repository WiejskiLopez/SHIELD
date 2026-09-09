"""Koncept: każdy query service obsługuje wyłącznie własny agregat.

Reguła: query service nie importuje domenowych portów repozytoriów ani modeli
persistence należących do innego agregatu.

Poprawnie: odczyt wieloagregatowy nie jest ukrywany w query service agregatu.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from _arch_helpers import BASE, architecture_assertion_message, iter_py_files, parse_file

if TYPE_CHECKING:
    from pathlib import Path

_QUERY_SERVICE_SUFFIX = "QueryService"
_REPOSITORY_MODULE_MARKER = ".repositories"
_MODEL_MODULE_MARKER = ".persistence."
_PREFIXES = ("Sql", "InMemory")


def _query_service_classes(path: Path, tree: ast.Module) -> list[str]:
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name.endswith(_QUERY_SERVICE_SUFFIX)
    ]


def _aggregate_name(class_name: str) -> str:
    name = class_name.removesuffix(_QUERY_SERVICE_SUFFIX)
    for prefix in _PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _import_modules(tree: ast.Module) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_query_services_use_only_their_own_aggregate_data() -> None:
    violations: list[str] = []
    for path in iter_py_files(BASE):
        if "infrastructure" not in path.parts:
            continue
        tree = parse_file(path)
        if tree is None:
            continue
        for class_name in _query_service_classes(path, tree):
            aggregate = _aggregate_name(class_name)
            for module in _import_modules(tree):
                if _REPOSITORY_MODULE_MARKER in module and ".domain." in module:
                    violations.append(
                        f"{path.relative_to(BASE)}:{class_name} imports domain repository {module}"
                    )
                if _MODEL_MODULE_MARKER not in module:
                    continue
                imported_aggregates = [
                    segment
                    for segment in module.split(".")
                    if segment.endswith(("_execution", "_definition", "_state", "_config"))
                ]
                if imported_aggregates and aggregate not in imported_aggregates:
                    violations.append(
                        f"{path.relative_to(BASE)}:{class_name} ({aggregate}) imports {module}"
                    )
    assert not violations, architecture_assertion_message(
        "query service aggregate boundary",
        "query service reads only its own aggregate and does not use domain repositories",
        "\n".join(violations),
    )
