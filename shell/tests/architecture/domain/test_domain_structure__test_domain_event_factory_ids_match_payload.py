"""Koncept: spójność identyfikatorów zdarzeń domenowych.

Reguła: fabryka DomainEvent przekazuje identyfikatory zgodne z payloadem.
Poprawnie: identyfikatory agregatu i zdarzenia są zachowane w kontrakcie eventu.
"""

from __future__ import annotations

import ast

from _arch_helpers import (
    BASE,
    architecture_assertion_message,
    extends_any_base,
    find_classes,
    iter_py_files,
    parse_file,
)

_EVENT_BASES = {"DomainEvent"}


def _inherits_event(node: ast.ClassDef) -> bool:
    return extends_any_base(node, _EVENT_BASES)


def _field_names(node: ast.ClassDef) -> set[str]:
    return {
        stmt.target.id
        for stmt in node.body
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
    }


def _factory_id_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    return {
        argument.arg
        for argument in arguments
        if argument.arg not in {"self", "cls"} and argument.arg.endswith("_id")
    }


def test_domain_events_have_no_aggregate_id_and_factory_ids_match_payload() -> None:
    violations: list[str] = []

    for path in iter_py_files(BASE):
        tree = parse_file(path)
        if tree is None:
            continue
        for event in find_classes(tree):
            if not _inherits_event(event):
                continue
            if event.name.startswith("_"):
                continue

            fields = _field_names(event)
            if "aggregate_id" in fields:
                violations.append(f"{path}: {event.name}.aggregate_id")
            aggregate_index = path.parts.index("aggregates")
            aggregate_name = path.parts[aggregate_index + 1]
            aggregate_id_field = f"{aggregate_name}_id"
            if aggregate_id_field not in fields:
                violations.append(
                    f"{path}: {event.name} must define its aggregate ID field "
                    f"{aggregate_id_field!r}, found {sorted(fields)!r}"
                )

            for member in event.body:
                if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if member.name != "now":
                    continue
                for parameter in sorted(_factory_id_params(member) - fields):
                    violations.append(
                        f"{path}: {event.name}.now() has unrelated ID parameter "
                        f"{parameter!r}"
                    )

    assert not violations, architecture_assertion_message(
        "reguła testowana przez test_domain_events_have_no_aggregate_id_and_factory_ids_match_payload",
        "DomainEvent nie posiada aggregate_id, a fabryka przekazuje tylko ID zapisane w payloadzie",
        "DomainEvent identity contract violations:\n" + "\n".join(violations),
    )
