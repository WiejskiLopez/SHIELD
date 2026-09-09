"""Koncept: własność topologii domeny bounded contextów.

Reguła: eventy pozostają przy agregatach, a współdzielone value objects mają jawne wyjątki.
Poprawnie: topologia domeny nie zawiera nieuprawnionych fasad BC-level.
"""

from pathlib import Path

_BASE = Path(__file__).resolve().parents[3]
_SERVICES = ("definition", "execution", "ingestion", "project", "scheduling", "session", "user")
_SHARED_VALUE_OBJECT_SERVICES = {"session", "user"}


def test_domain_events_and_value_objects_stay_under_aggregates() -> None:
    violations: list[str] = []
    for service in _SERVICES:
        domain = _BASE / f"{service}_service" / "domain" / service
        events_directory = domain / "events"
        if events_directory.exists():
            files = [path for path in events_directory.glob("*.py") if path.name != "__init__.py"]
            violations.extend(str(path.relative_to(_BASE)) for path in files)

        directory_name = "value_objects"
        directory = domain / directory_name
        if not directory.exists() or service in _SHARED_VALUE_OBJECT_SERVICES:
            continue
        files = [path for path in directory.glob("*.py") if path.name != "__init__.py"]
        violations.extend(str(path.relative_to(_BASE)) for path in files)

    assert not violations, "New BC-level domain modules must live under an aggregate:\n" + "\n".join(
        violations
    )
