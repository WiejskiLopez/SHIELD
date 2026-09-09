"""Schema audits comparing migrated SQLite databases with ORM metadata."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import DateTime, create_engine, inspect
from sqlalchemy.schema import ForeignKeyConstraint, UniqueConstraint

from shell.definition_service.migrations.baseline import run_definition_baseline
from shell.execution_service.migrations.baseline import run_execution_baseline
from shell.ingestion_service.migrations.baseline import run_ingestion_baseline
from shell.platform.infrastructure.persistence.service_metadata import service_metadata
from shell.project_service.migrations.baseline import run_project_baseline
from shell.scheduling_service.migrations.baseline import run_scheduling_baseline
from shell.session_service.migrations.baseline import run_session_baseline
from shell.user_service.migrations.baseline import run_user_baseline

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine, MetaData, Table

_MigrationRunner = Callable[[str, bool], Awaitable[None]]
_ServiceSpec = tuple[str, str, str, str, _MigrationRunner]

_SERVICE_SPECS: tuple[_ServiceSpec, ...] = (
    (
        "definition",
        "shell.definition_service",
        "shell.definition_service.infrastructure.definition.persistence.sql.models.base",
        "DefinitionSqlAlchemyModelBase",
        run_definition_baseline,
    ),
    (
        "execution",
        "shell.execution_service",
        "shell.execution_service.infrastructure.execution.persistence.sql.models.base",
        "ExecutionSqlAlchemyModelBase",
        run_execution_baseline,
    ),
    (
        "ingestion",
        "shell.ingestion_service",
        "shell.ingestion_service.infrastructure.ingestion.persistence.sql.models.base",
        "IngestionSqlAlchemyModelBase",
        run_ingestion_baseline,
    ),
    (
        "project",
        "shell.project_service",
        "shell.project_service.infrastructure.project.persistence.sql.models.base",
        "ProjectSqlAlchemyModelBase",
        run_project_baseline,
    ),
    (
        "scheduling",
        "shell.scheduling_service",
        "shell.scheduling_service.infrastructure.scheduling.persistence.sql.models.base",
        "SchedulingSqlAlchemyModelBase",
        run_scheduling_baseline,
    ),
    (
        "session",
        "shell.session_service",
        "shell.session_service.infrastructure.session.persistence.sql.models.base",
        "SessionSqlAlchemyModelBase",
        run_session_baseline,
    ),
    (
        "user",
        "shell.user_service",
        "shell.user_service.infrastructure.user.persistence.sql.models.base",
        "UserSqlAlchemyModelBase",
        run_user_baseline,
    ),
)

_VERSION_TABLES = frozenset({"alembic_version", "platform_alembic_version"})
_PLATFORM_TABLES = frozenset(
    {
        "event_outbox",
        "event_inbox",
        "command_outbox",
        "command_inbox",
        "audit_event",
        "worker_heartbeat",
    }
)


def _type_signature(column_type: object, engine: Engine) -> str:
    return str(column_type.compile(dialect=engine.dialect)).split("(", maxsplit=1)[0].upper()


def _metadata_index_signature(index: object) -> tuple[str, tuple[str, ...], bool]:
    return (index.name, tuple(column.name for column in index.columns), False)


def _inspector_index_signature(index: dict[str, object]) -> tuple[str, tuple[str, ...], bool]:
    return (
        str(index["name"]),
        tuple(str(column) for column in index["column_names"]),
        bool(index["unique"]),
    )


def _metadata_unique_signature(constraint: UniqueConstraint) -> tuple[str, tuple[str, ...]]:
    return (constraint.name or "", tuple(column.name for column in constraint.columns))


def _inspector_unique_signature(constraint: dict[str, object]) -> tuple[str, tuple[str, ...]]:
    return (
        str(constraint.get("name") or ""),
        tuple(str(column) for column in constraint["column_names"]),
    )


def _foreign_key_signature(constraint: ForeignKeyConstraint) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(element.parent.name for element in constraint.elements),
        tuple(element.target_fullname for element in constraint.elements),
    )


def _inspect_foreign_key_signature(constraint: dict[str, object]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    referred_table = str(constraint["referred_table"])
    return (
        tuple(str(column) for column in constraint["constrained_columns"]),
        tuple(
            f"{referred_table}.{column}" for column in constraint["referred_columns"]
        ),
    )


def _audit_table(table: Table, inspector: object, engine: Engine) -> list[str]:
    violations: list[str] = []
    actual_columns = {column["name"]: column for column in inspector.get_columns(table.name)}
    expected_columns = {column.name for column in table.columns}
    missing_columns = expected_columns - set(actual_columns)
    unexpected_columns = set(actual_columns) - expected_columns
    for column in sorted(missing_columns):
        violations.append(f"{table.name}: missing column {column}")
    for column in sorted(unexpected_columns):
        violations.append(f"{table.name}: unexpected column {column}")

    for column in table.columns:
        actual = actual_columns.get(column.name)
        if actual is None:
            continue
        if bool(actual["nullable"]) != bool(column.nullable):
            violations.append(
                f"{table.name}.{column.name}: nullable={actual['nullable']!r}, "
                f"ORM={column.nullable!r}"
            )
        actual_type = _type_signature(actual["type"], engine)
        expected_type = _type_signature(column.type, engine)
        if actual_type != expected_type:
            violations.append(
                f"{table.name}.{column.name}: type={actual_type}, ORM={expected_type}"
            )

    actual_primary_key = tuple(inspector.get_pk_constraint(table.name)["constrained_columns"])
    expected_primary_key = tuple(column.name for column in table.primary_key.columns)
    if actual_primary_key != expected_primary_key:
        violations.append(
            f"{table.name}: primary key={actual_primary_key!r}, ORM={expected_primary_key!r}"
        )

    actual_foreign_keys = {
        _inspect_foreign_key_signature(constraint)
        for constraint in inspector.get_foreign_keys(table.name)
    }
    expected_foreign_keys = {
        _foreign_key_signature(constraint)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    if actual_foreign_keys != expected_foreign_keys:
        violations.append(
            f"{table.name}: foreign keys={actual_foreign_keys!r}, ORM={expected_foreign_keys!r}"
        )

    actual_indexes = {
        _inspector_index_signature(index) for index in inspector.get_indexes(table.name)
    }
    expected_indexes = {
        _metadata_index_signature(index) for index in table.indexes
    }
    if actual_indexes != expected_indexes:
        violations.append(
            f"{table.name}: indexes={actual_indexes!r}, ORM={expected_indexes!r}"
        )

    actual_unique_constraints = {
        _inspector_unique_signature(constraint)
        for constraint in inspector.get_unique_constraints(table.name)
    }
    expected_unique_constraints = {
        _metadata_unique_signature(constraint)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    if actual_unique_constraints != expected_unique_constraints:
        violations.append(
            f"{table.name}: unique constraints={actual_unique_constraints!r}, "
            f"ORM={expected_unique_constraints!r}"
        )
    return violations


@pytest.mark.integration
async def test_migrated_schema_matches_orm_metadata(tmp_path: Path) -> None:
    violations: list[str] = []
    for service_name, package, base_module, base_class, run_migrations in _SERVICE_SPECS:
        database_url = f"sqlite+aiosqlite:///{tmp_path / f'{service_name}.db'}"
        await run_migrations(database_url)
        engine = create_engine(database_url.replace("+aiosqlite", ""))
        metadata: MetaData = service_metadata(package, base_module, base_class)
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names()) - _VERSION_TABLES
        expected_tables = set(metadata.tables)
        for table_name in sorted(expected_tables - actual_tables):
            violations.append(f"{service_name}: missing table {table_name}")
        for table_name in sorted(actual_tables - expected_tables):
            violations.append(f"{service_name}: unexpected table {table_name}")
        for table_name in sorted(expected_tables & actual_tables):
            violations.extend(
                f"{service_name}: {violation}"
                for violation in _audit_table(metadata.tables[table_name], inspector, engine)
            )
        engine.dispose()

    assert not violations, "Migrated schema differs from ORM metadata:\n" + "\n".join(violations)


@pytest.mark.integration
async def test_platform_timestamps_are_timezone_aware() -> None:
    violations: list[str] = []
    for _, package, base_module, base_class, _ in _SERVICE_SPECS:
        metadata: MetaData = service_metadata(package, base_module, base_class)
        for table_name in _PLATFORM_TABLES:
            table = metadata.tables.get(table_name)
            if table is None:
                continue
            for column in table.columns:
                if isinstance(column.type, DateTime) and not column.type.timezone:
                    violations.append(f"{table_name}.{column.name}: timezone=True is required")

    assert not violations, "Platform timestamp columns must be timezone-aware:\n" + "\n".join(
        violations
    )
