"""Koncept: query service należy do jednego agregatu.

Reguła: query service musi znajdować się pod infrastructure/<bc>/<aggregate>/persistence.

Poprawnie: katalog infrastructure/<bc>/persistence nie zawiera klas query service.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from _arch_helpers import BASE, architecture_assertion_message, iter_py_files, parse_file

if TYPE_CHECKING:
    from pathlib import Path


def _is_bc_wide_persistence(path: Path) -> bool:
    parts = path.relative_to(BASE).parts
    return (
        len(parts) >= 5
        and parts[0].endswith("_service")
        and parts[1] == "infrastructure"
        and parts[3] == "persistence"
    )


def _query_service_classes(tree: ast.Module) -> list[str]:
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name.endswith("QueryService")
    ]


def test_query_services_are_nested_under_their_aggregate() -> None:
    violations: list[str] = []
    for path in iter_py_files(BASE):
        if not _is_bc_wide_persistence(path):
            continue
        tree = parse_file(path)
        if tree is None:
            continue
        for class_name in _query_service_classes(tree):
            violations.append(
                f"{path.relative_to(BASE)}:{class_name} must be under an aggregate persistence directory"
            )
    assert not violations, architecture_assertion_message(
        "query service topology",
        "query services must live under infrastructure/<bc>/<aggregate>/persistence",
        "\n".join(violations),
    )