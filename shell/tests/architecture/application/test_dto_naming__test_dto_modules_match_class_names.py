"""Koncept: reguła nazewnictwa modułów application DTO.

Reguła: każda klasa kończąca się na ``Dto`` żyje w module o nazwie
``<class_name>_dto.py``.

Poprawnie: nazwa modułu jednoznacznie identyfikuje projekcję DTO.
"""

from __future__ import annotations

import ast

from _arch_helpers import (
    BASE,
    architecture_assertion_message,
    iter_named_dirs,
    parse_file,
    to_snake_case,
)


def test_dto_modules_match_class_names() -> None:
    violations: list[str] = []
    for dto_dir in iter_named_dirs("application", "dto"):
        for path in dto_dir.glob("*.py"):
            if path.name == "__init__.py":
                continue
            tree = parse_file(path)
            if tree is None:
                continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or not node.name.endswith("Dto"):
                    continue
                expected = f"{to_snake_case(node.name)}.py"
                if path.name != expected:
                    violations.append(
                        f"{path.relative_to(BASE)}: {node.name} should be defined in {expected}"
                    )

    assert not violations, architecture_assertion_message(
        "reguła testowana przez test_dto_modules_match_class_names",
        "warunek zapisany w asercji musi być spełniony",
        "Application DTO modules must match their class names:\n" + "\n".join(violations),
    )
