"""Koncept: zero Any na ścieżce sagi.

Reguła: kod produkcyjny nowego drzewa libki oraz warstwy process właścicieli
(project, scheduling) nie zawierają adnotacji ani castów na `Any` (jedyny wyjątek:
parametr `__eq__`, idiom typeshed). Liczby i identyfikatory noszą dedykowane typy.

Poprawnie: sygnatury używają VO/portów/protokołów zamiast Any/object.
"""

from __future__ import annotations

import re

from _arch_helpers import BASE, architecture_assertion_message
from saga_topology_paths import new_tree_files, saga_python_files


def test_no_any_in_saga_path() -> None:
    offenders: list[str] = []
    roots = list(new_tree_files())
    roots.extend(saga_python_files(BASE / "project_service" / "process"))
    roots.extend(saga_python_files(BASE / "scheduling_service" / "process"))
    for path in roots:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r":\s*Any\b|cast\(\s*['\"]Any['\"]", line):
                offenders.append(f"{path}:{number}:{line.strip()}")
    assert not offenders, architecture_assertion_message(
        "test_no_any_in_saga_path",
        "Any w ścieżce sagi",
        offenders,
    )
