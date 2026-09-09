"""Koncept: jawne subskrypcje konsumentów eventów.

Reguła: każdy konsument deklaruje routing keys.
Poprawnie: broker nie otrzymuje niejawnej subskrypcji.
"""

import ast

from _arch_helpers import BASE


def test_event_consumers_declare_routing_keys() -> None:
    violations: list[str] = []
    for path in BASE.glob("*_service/bootstrap/**/container/*_core_container.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            if not any(
                isinstance(node, ast.Name) and node.id == "EventInboxConsumer"
                for node in ast.walk(call.func)
            ):
                continue
            if not any(keyword.arg == "routing_keys" for keyword in call.keywords):
                violations.append(path.relative_to(BASE).as_posix())

    assert not violations, "EventInboxConsumer factories must declare routing_keys:\n" + "\n".join(
        sorted(violations)
    )