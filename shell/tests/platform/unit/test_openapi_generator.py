"""Contract tests for the generated multi-service OpenAPI document."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_PATH = Path(__file__).parents[4] / "scripts" / "generate-openapi.py"
_SCRIPT_SPEC = importlib.util.spec_from_file_location("generate_openapi", _SCRIPT_PATH)
assert _SCRIPT_SPEC is not None
assert _SCRIPT_SPEC.loader is not None
_SCRIPT_MODULE = importlib.util.module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(_SCRIPT_MODULE)


EXPECTED_SERVICES = {
    "definition",
    "execution",
    "ingestion",
    "project",
    "scheduling",
    "session",
    "user",
}


def test_generator_builds_all_bounded_context_specs() -> None:
    specs = _SCRIPT_MODULE._build_specs()

    assert set(specs) == EXPECTED_SERVICES
    for spec in specs.values():
        assert "/health" in spec["paths"]
        assert "/openapi.json" not in spec["paths"]
        schemas = spec["components"]["schemas"]
        assert {"ProblemDetail", "Page", "FieldError"}.issubset(schemas)
