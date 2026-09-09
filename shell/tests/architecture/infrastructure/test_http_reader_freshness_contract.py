"""Koncept: świeżość odczytów HTTP.

Reguła: reader wykonuje nowe żądanie dla każdego odczytu.
Poprawnie: produkcja nie używa usuniętego cache odczytów.
"""

from __future__ import annotations

import ast

from _arch_helpers import BASE, architecture_assertion_message, parse_file

_READER_FILES = (
    BASE
    / "execution_service/infrastructure/execution/graph_execution/adapters/graph_definition/graph_definition_reader_http_adapter.py",
    BASE
    / "execution_service/infrastructure/execution/node_execution/adapters/node_definition/node_definition_reader_http_adapter.py",
    BASE
    / "execution_service/infrastructure/execution/session_execution/adapters/session_reader/session_reader_http_adapter.py",
)


def test_http_readers_do_not_define_local_cache_state() -> None:
    violations: list[str] = []
    for path in _READER_FILES:
        tree = parse_file(path)
        if tree is None:
            violations.append(f"{path}: plik nie parsuje się poprawnie")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                assignments: list[str] = []
                for statement in ast.walk(node):
                    targets: list[ast.expr] = []
                    if isinstance(statement, ast.Assign):
                        targets.extend(statement.targets)
                    elif isinstance(statement, ast.AnnAssign):
                        targets.append(statement.target)
                    for target in targets:
                        if isinstance(target, ast.Name):
                            assignments.append(target.id)
                        elif isinstance(target, ast.Attribute):
                            assignments.append(target.attr)
                cache_names = [name for name in assignments if "cache" in name.lower()]
                if cache_names:
                    violations.append(f"{path}: lokalny stan cache {cache_names}")

    assert not violations, architecture_assertion_message(
        "reader HTTP musi pobierać świeże dane",
        "adapter nie posiada lokalnego cache ani stanu cache",
        "\n".join(violations),
    )
