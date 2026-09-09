"""Koncept: niezależność biblioteki sagi od platformy SHELL.

Reguła: żaden plik nowego drzewa `saga_orchestration` (domain/application/
sqlalchemy/in_memory/dispatcher/worker/backlog/bootstrap) nie importuje
`shell.*` — ani w runtime, ani w TYPE_CHECKING, ani w komentarzach.

Poprawnie: libka definiuje porty, serwis dostarcza adaptery (SAGA.MD Krok 2).
"""

from __future__ import annotations

import ast

from _arch_helpers import architecture_assertion_message
from saga_topology_paths import new_tree_files


def test_saga_package_does_not_import_shell() -> None:
    offenders: dict[str, list[int]] = {}
    for path in new_tree_files():
        lines: list[int] = []
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("shell"):
                lines.append(node.lineno)
            if isinstance(node, ast.Import):
                lines += [n.lineno for n in node.names if n.name.startswith("shell")]
        if lines:
            offenders[str(path)] = lines
    assert not offenders, architecture_assertion_message(
        "test_saga_package_does_not_import_shell",
        "nowe drzewo sagi importuje shell.* (łamie Krok 2)",
        [f"{path}:{lines}" for path, lines in offenders.items()],
    )
