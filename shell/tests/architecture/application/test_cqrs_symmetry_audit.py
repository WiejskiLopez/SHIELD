"""Koncept: jawny podział CQRS agregatów.

Reguła: każdy agregat należy do dokładnie jednej kategorii CQRS.
Poprawnie: inventory jest jawne i nie dryfuje bez decyzji.
"""

from __future__ import annotations

from pathlib import Path

from _arch_helpers import architecture_assertion_message

BASE = Path(__file__).resolve().parents[3]
_SERVICE_NAMES = ("definition", "execution", "ingestion", "project", "scheduling", "session", "user")
_NON_AGGREGATE_DIRS = {"commands", "command_handlers", "event_handlers", "queries", "query_handlers"}
_EXPECTED_CQRS_INVENTORY = {
    "both": frozenset(
        {
            "definition.node_definition",
            "execution.edge_execution",
            "execution.edge_link_execution",
            "execution.node_execution",
            "execution.task_execution",
            "execution.workflow",
            "ingestion.ingestion",
            "project.project",
            "session.session",
            "scheduling.scheduler_definition",
            "scheduling.scheduler_execution",
            "scheduling.scheduler_job",
            "user.auth_session",
            "user.user",
        }
    ),
    "commands": frozenset(
        {
            "project.project_provision",
            "scheduling.scheduler_provision",
        }
    ),
    "queries": frozenset(
        {
            "definition.graph_definition",
            "definition.runner_config",
            "execution.agent_config_execution",
            "execution.agent_execution",
            "execution.agent_skill_execution",
            "execution.graph_execution",
            "execution.session_execution",
            "execution.task_execution_state",
            "execution.user_execution",
            "execution.user_execution_state",
            "project.project_skill",
            "session.session_state",
            "user.user_skill",
            "user.user_state",
        }
    ),
    "none": frozenset(
        {
            "definition.graph_definition_embedding",
            "definition.node_link_definition",
            "execution.graph_execution_state",
            "execution.node_execution_state",
            "execution.node_link_execution",
            "execution.session_execution_state",
            "execution.workflow_state",
            "project.project_state",
        }
    ),
}

_KNOWN_CQRS_GAPS = frozenset(
    {
        "definition.graph_definition_embedding",
        "definition.node_link_definition",
        "execution.graph_execution_state",
        "execution.node_execution_state",
        "execution.node_link_execution",
        "execution.session_execution_state",
        "execution.workflow_state",
        "project.project_state",
    }
)


def _aggregate_names(service: str) -> list[str]:
    application = BASE / f"{service}_service" / "application" / service
    return sorted(
        path.name
        for path in application.iterdir()
        if path.is_dir()
        and not path.name.startswith("__")
        and path.name not in _NON_AGGREGATE_DIRS
    )


def _has_python_files(path: Path) -> bool:
    return any(candidate.suffix == ".py" for candidate in path.glob("*.py"))


def _check_each_aggregate_has_explicit_cqrs_inventory() -> None:
    gaps: set[str] = set()
    for service in _SERVICE_NAMES:
        application = BASE / f"{service}_service" / "application" / service
        for aggregate in _aggregate_names(service):
            aggregate_dir = application / aggregate
            has_commands = _has_python_files(aggregate_dir / "commands")
            has_queries = _has_python_files(aggregate_dir / "queries")
            if not has_commands and not has_queries:
                gaps.add(f"{service}.{aggregate}")

    assert gaps == _KNOWN_CQRS_GAPS, architecture_assertion_message(
        "test_each_aggregate_has_explicit_cqrs_inventory",
        "lista wyjątków CQRS jest jawna i nie dryfuje bez decyzji architektonicznej",
        f"Expected gaps: {sorted(_KNOWN_CQRS_GAPS)}; observed gaps: {sorted(gaps)}",
    )


def _check_cqrs_inventory_categories_are_explicit() -> None:
    observed: dict[str, set[str]] = {category: set() for category in _EXPECTED_CQRS_INVENTORY}
    for service in _SERVICE_NAMES:
        application = BASE / f"{service}_service" / "application" / service
        for aggregate in _aggregate_names(service):
            aggregate_dir = application / aggregate
            has_commands = _has_python_files(aggregate_dir / "commands")
            has_queries = _has_python_files(aggregate_dir / "queries")
            category = (
                "both"
                if has_commands and has_queries
                else "commands"
                if has_commands
                else "queries"
                if has_queries
                else "none"
            )
            observed[category].add(f"{service}.{aggregate}")

    expected = {category: set(values) for category, values in _EXPECTED_CQRS_INVENTORY.items()}
    assert observed == expected, architecture_assertion_message(
        "test_cqrs_inventory_categories_are_explicit",
        "każdy agregat ma jawną, uzasadnioną kategorię CQRS",
        f"Expected: {expected}; observed: {observed}",
    )


def test_cqrs_inventory_contract() -> None:
    _check_each_aggregate_has_explicit_cqrs_inventory()
    _check_cqrs_inventory_categories_are_explicit()
