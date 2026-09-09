"""Koncept: liniowość łańcuchów migracji Alembic.

Reguła: każdy katalog migrations/versions ma kompletny, liniowy łańcuch rewizji
bez luk i odłączonych gałęzi.

Poprawnie: audyt nie zgłasza brakujących down_revision, duplikatów ani luk
w numeracji.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from _arch_helpers import BASE, architecture_assertion_message

if TYPE_CHECKING:
    from pathlib import Path

_MIGRATION_NAME = re.compile(r"^[a-z0-9]+_(\d{4})_")


def _migration_roots() -> tuple[Path, ...]:
    roots = [BASE / "migrations" / "versions"]
    roots.extend(BASE.glob("*_service/migrations/versions"))
    return tuple(sorted(root for root in roots if root.is_dir()))


def _module_constant(path: Path, name: str) -> object:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return _literal_value(node.value)
    return _MISSING


def _literal_value(node: ast.expr) -> object:
    if isinstance(node, ast.Constant) and (isinstance(node.value, str) or node.value is None):
        return node.value
    if isinstance(node, ast.Tuple):
        values = tuple(_literal_value(element) for element in node.elts)
        if all(isinstance(value, str) for value in values):
            return values
    return _MISSING


class _Missing:
    pass


_MISSING = _Missing()


def _down_revisions(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
        return value
    return ()


def _audit_root(root: Path) -> list[str]:
    files = sorted(path for path in root.glob("*.py") if path.name != "__init__.py")
    revisions: dict[str, tuple[Path, tuple[str, ...]]] = {}
    violations: list[str] = []

    for path in files:
        revision = _module_constant(path, "revision")
        down_revision = _module_constant(path, "down_revision")
        relative = path.relative_to(BASE).as_posix()
        if not isinstance(revision, str):
            violations.append(f"{relative}: revision musi być stringiem")
            continue
        if down_revision is _MISSING:
            violations.append(f"{relative}: brak down_revision")
            continue
        if revision in revisions:
            violations.append(f"{relative}: zduplikowana revision {revision}")
            continue
        revisions[revision] = (path, _down_revisions(down_revision))

    if not revisions:
        return violations

    referenced = {
        target
        for _, down_revisions in revisions.values()
        for target in down_revisions
    }
    roots = [revision for revision, (_, down_revisions) in revisions.items() if not down_revisions]
    heads = [revision for revision in revisions if revision not in referenced]

    for _revision, (path, down_revisions) in revisions.items():
        relative = path.relative_to(BASE).as_posix()
        missing = sorted(set(down_revisions) - revisions.keys())
        if missing:
            violations.append(f"{relative}: brak down_revision {missing}")

    if len(roots) != 1:
        violations.append(f"{root.relative_to(BASE).as_posix()}: oczekiwano 1 root, znaleziono {roots}")
    if len(heads) != 1:
        violations.append(f"{root.relative_to(BASE).as_posix()}: oczekiwano 1 head, znaleziono {heads}")

    numbered = []
    for path in files:
        match = _MIGRATION_NAME.match(path.stem)
        if match:
            numbered.append((int(match.group(1)), path))
    numbers = sorted(number for number, _ in numbered)
    if numbers and numbers != list(range(numbers[0], numbers[-1] + 1)):
        violations.append(
            f"{root.relative_to(BASE).as_posix()}: luka w numeracji migracji: {numbers}"
        )

    return violations


def test_all_migration_revision_chains_are_linear() -> None:
    violations = [violation for root in _migration_roots() for violation in _audit_root(root)]

    assert not violations, architecture_assertion_message(
        "test_all_migration_revision_chains_are_linear",
        "każdy katalog migracji ma kompletny, liniowy łańcuch rewizji bez luk",
        "\n".join(violations),
    )
