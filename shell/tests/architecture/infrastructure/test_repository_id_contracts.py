"""Koncept: typowane operacje tożsamości repozytoriów.

Reguła: get, delete i exists przyjmują domenowe typy ID.
Poprawnie: repozytoria nie używają prymitywnych identyfikatorów.
"""

import ast
from pathlib import Path

_SHELL = Path(__file__).resolve().parents[3]
_IDENTITY_METHODS = {"get_by_id", "delete", "exists"}


def _contains_object_annotation(node: ast.arg) -> bool:
    return any(isinstance(child, ast.Name) and child.id == "object" for child in ast.walk(node.annotation))


def test_repository_identity_methods_do_not_accept_object() -> None:
    violations: list[str] = []
    for path in _SHELL.glob("**/repositories/*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name not in _IDENTITY_METHODS:
                continue
            for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                if argument.annotation is not None and _contains_object_annotation(argument):
                    relative = path.relative_to(_SHELL).as_posix()
                    violations.append(f"{relative}:{node.lineno} {node.name}({argument.arg}: object)")

    assert not violations, "Repository identity methods must use concrete ID types:\n" + "\n".join(
        violations
    )