"""Koncept: reguła architektoniczna dotycząca uow mapper contract.

Reguła: test sprawdza kontrakt architektoniczny uow mapper contract.

Poprawnie: kod spełnia ten kontrakt i nie zgłasza naruszeń.
"""

from __future__ import annotations

import ast

from _arch_helpers import (
    BASE,
    architecture_assertion_message,
    find_classes,
    iter_py_files,
    parse_file,
)

_UOW_BASES = tuple(BASE.glob("*_service/infrastructure"))
_KNOWN_NON_UOW_EXTENDERS: frozenset[str] = frozenset()


def _check_per_bc_uow_accepts_mapper() -> None:
    violations: list[str] = []
    for uow_base in _UOW_BASES:
        for py_file in iter_py_files(uow_base):
            if py_file.name != "unit_of_work.py":
                continue
            rel = py_file.relative_to(BASE)
            tree = parse_file(py_file)
            if tree is None:
                continue
            for class_node in find_classes(tree):
                bases = {b.id for b in class_node.bases if isinstance(b, ast.Name)}
                if "SqlAlchemyUnitOfWorkBase" not in bases:
                    continue
                key = f"{rel}: class {class_node.name}"
                if key in _KNOWN_NON_UOW_EXTENDERS:
                    continue
                required_params = {"mapper", "source_service", "models"}
                constructor_params: set[str] = set()
                forwarded_params: set[str] = set()
                optional_params: set[str] = set()
                for stmt in class_node.body:
                    if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
                        positional_params = [*stmt.args.posonlyargs, *stmt.args.args]
                        constructor_params = {arg.arg for arg in positional_params}
                        defaults = [None] * (len(positional_params) - len(stmt.args.defaults))
                        defaults.extend(stmt.args.defaults)
                        optional_params = {
                            arg.arg
                            for arg, default in zip(positional_params, defaults, strict=True)
                            if default is not None
                        }
                        for node_in_init in ast.walk(stmt):
                            if (
                                isinstance(node_in_init, ast.Call)
                                and isinstance(node_in_init.func, ast.Attribute)
                                and (node_in_init.func.attr == "__init__")
                            ):
                                forwarded_params.update(
                                    kw.arg for kw in node_in_init.keywords if kw.arg is not None
                                )
                missing_params = required_params - constructor_params
                if missing_params:
                    violations.append(
                        f"{key}: brak parametrów {sorted(missing_params)} w __init__"
                    )
                missing_forwarding = required_params - forwarded_params
                if missing_forwarding:
                    violations.append(
                        f"{key}: brak przekazania {sorted(missing_forwarding)} do super().__init__"
                    )
                optional_required = required_params & optional_params
                if optional_required:
                    violations.append(
                        f"{key}: wymagane parametry mają wartości domyślne {sorted(optional_required)}"
                    )
    assert not violations, architecture_assertion_message(
        "reguła testowana przez test_per_bc_uow_accepts_mapper",
        "warunek zapisany w asercji musi być spełniony",
        "Naruszona reguła: UoW musi przyjmować i przekazywać mapper.\nZnaleziono:\n"
        + "\n".join(violations)
        + "\nJak naprawić: dodaj mapper=mapper do konstruktora bazowego UoW.",
    )


def _check_base_uow_does_not_derive_source_service_from_class() -> None:
    base_file = BASE / "platform/infrastructure/persistence/sql_alchemy_uow_base.py"
    tree = parse_file(base_file)
    assert tree is not None

    constructors = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    ]
    assert len(constructors) == 1
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "source_service_for_type"
        for node in ast.walk(constructors[0])
    )


def test_uow_mapper_contract() -> None:
    _check_per_bc_uow_accepts_mapper()
    _check_base_uow_does_not_derive_source_service_from_class()
