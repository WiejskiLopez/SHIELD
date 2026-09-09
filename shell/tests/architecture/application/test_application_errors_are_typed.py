"""Koncept: typowane błędy na granicy warstwy application.

Reguła: komendy i handlery application nie mogą rzucać wprost ValueError.

Poprawnie: walidacja wejścia używa ApplicationError-derived exception,
np. RequiredCommandFieldError albo InvalidCommandFieldError.
"""

from __future__ import annotations

import ast

from _arch_helpers import architecture_assertion_message, iter_layer_files, parse_file


def test_application_code_does_not_raise_value_error() -> None:
    violations: list[str] = []
    for path in iter_layer_files("application"):
        tree = parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            if isinstance(node.exc.func, ast.Name) and node.exc.func.id == "ValueError":
                violations.append(f"{path}: line {node.lineno}")
    assert not violations, architecture_assertion_message(
        "test_application_errors_are_typed",
        "application commands use concrete ApplicationError-derived exceptions",
        "ValueError is forbidden in application command validation:\n" + "\n".join(violations),
    )
