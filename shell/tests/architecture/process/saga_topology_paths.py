"""Wspólne ścieżki strażników sagi (SAGA.MD Krok 8). Moduł pomocniczy, nie test."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from _arch_helpers import BASE

if TYPE_CHECKING:
    from pathlib import Path

SAGA = BASE.parent / "packaging" / "saga-orchestration" / "saga_orchestration"
NEW_TREE = (
    SAGA / "domain",
    SAGA / "application",
    SAGA / "infrastructure" / "sqlalchemy",
    SAGA / "infrastructure" / "in_memory",
    SAGA / "bootstrap",
)
NEW_FILES = (
    SAGA / "infrastructure" / "dispatcher.py",
    SAGA / "infrastructure" / "saga_timeout_worker.py",
    SAGA / "infrastructure" / "timeout_backlog.py",
)

_SKIPPED_DIRS = frozenset({"__pycache__", ".venv", "build", "dist", ".git", ".hg"})


def saga_python_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    return [
        path for path in root.rglob("*.py") if not any(part in _SKIPPED_DIRS for part in path.parts)
    ]


def new_tree_files() -> list[Path]:
    files: list[Path] = []
    for root in NEW_TREE:
        files.extend(saga_python_files(root))
    files.extend(path for path in NEW_FILES if path.is_file())
    return files


SAGA_OWNERS = frozenset({"project_service", "scheduling_service"})
"""Serwisy-właściciele typów sag (SAGA.MD Krok 7, RFC-07)."""

SAGA_OWNER_BASE_MODULES = {
    "project_service": "shell.project_service.infrastructure.project.persistence.sql.models.base",
    "scheduling_service": "shell.scheduling_service.infrastructure.scheduling.persistence.sql.models.base",
}
"""Moduł `base.py` każdego właściciela (stąd `SAGA_MODELS`)."""

EXPECTED_SAGA_COLUMNS = {
    "saga_instance": frozenset(
        {
            "id",
            "saga_type",
            "saga_key",
            "status",
            "current_step",
            "business_payload",
            "completed_steps",
            "failed_steps",
            "compensation_stack",
            "compensation_cursor",
            "attempts",
            "version",
            "created_at",
            "updated_at",
            "completed_at",
            "failed_at",
            "compensated_at",
        }
    ),
    "saga_timeout": frozenset(
        {
            "id",
            "saga_id",
            "saga_type",
            "saga_key",
            "step",
            "attempt",
            "kind",
            "due_at",
            "status",
            "owner",
            "lease_until",
            "correlation_id",
            "causation_id",
        }
    ),
    "saga_processed_delivery": frozenset(
        {"delivery_id", "saga_id", "step", "attempt", "succeeded", "processed_at"}
    ),
}
"""Kontrakt kolumn DDL libki (RFC-02/03): modele serwisów muszą go spełniać 1:1."""


def saga_container_texts() -> dict[str, str]:
    """Treść kontenerów DI per serwis (`shell/*/bootstrap/*/container/*.py`)."""
    containers: dict[str, str] = {}
    for container in sorted(BASE.glob("*_service/bootstrap/*/container/*.py")):
        service = container.relative_to(BASE).parts[0]
        containers[service] = container.read_text(encoding="utf-8")
    return containers


def saga_module_constant(path: Path, name: str) -> str | None:
    """Wartość stałej modułowej `name` (revision/down_revision migracji)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
    return None
