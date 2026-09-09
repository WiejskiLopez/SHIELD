"""Koncept: publiczne fabryki agregatow.

Reguła: agregaty nie udostepniaja publicznej metody new().

Poprawnie: publiczna metoda tworzenia deleguje do prywatnego _new().
"""

from __future__ import annotations

import ast

from _arch_helpers import (
    architecture_assertion_message,
    extends_any_base,
    find_classes,
    iter_domain_files,
    parse_file,
)

_AGGREGATE_BASES = {"AggregateRoot"}


def test_aggregates_have_no_public_new_factory() -> None:
    violations: list[str] = []

    for path in iter_domain_files():
        tree = parse_file(path)
        if tree is None:
            continue
        for node in find_classes(tree):
            if not extends_any_base(node, _AGGREGATE_BASES):
                continue
            for statement in node.body:
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and statement.name == "new":
                    relative_path = path.relative_to(path.parents[3]).as_posix()
                    violations.append(f"{relative_path}: {node.name}.new()")

    assert not violations, architecture_assertion_message(
        "agregaty nie udostepniaja publicznej metody new()",
        "publiczna sciezka tworzenia ma nazwe wynikajaca z potrzeb domeny i wywoluje prywatny _new() jako jedyny bazowy konstruktor agregatu; publiczne new() omija jawny jezyk operacji domenowej i utrudnia odroznienie API od wewnetrznej implementacji fabryki",
        "\n".join(violations),
    )
