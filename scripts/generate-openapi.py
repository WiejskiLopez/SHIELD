#!/usr/bin/env python
"""Generates openapi.json from the FastAPI application."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

from shell.definition_service.framework.definition.api.app import create_definition_app
from shell.execution_service.framework.execution.api.app import create_execution_app
from shell.ingestion_service.framework.ingestion.api.app import create_ingestion_app
from shell.project_service.framework.project.project.api.app import create_project_app
from shell.scheduling_service.framework.scheduling.api.app import create_scheduling_app
from shell.session_service.framework.session.api.app import create_session_app
from shell.user_service.framework.user.api.app import create_user_app


def _build_specs() -> dict[str, dict[str, object]]:
    container = MagicMock()
    factories = {
        "definition": lambda: create_definition_app(container, api_key="openapi-generation-placeholder"),
        "execution": lambda: create_execution_app(container, api_key="openapi-generation-placeholder"),
        "ingestion": lambda: create_ingestion_app(container, api_key="openapi-generation-placeholder"),
        "project": lambda: create_project_app(container, api_key="openapi-generation-placeholder"),
        "scheduling": lambda: create_scheduling_app(container, api_key="openapi-generation-placeholder"),
        "session": lambda: create_session_app(container, api_key="openapi-generation-placeholder"),
        "user": lambda: create_user_app(
            container,
            api_key="openapi-generation-placeholder",
            jwt_secret=os.environ.get(
                "OPENAPI_GENERATION_JWT_SECRET",
                "openapi-jwt-generation-placeholder",
            ),
        ),
    }
    return {name: factory().openapi() for name, factory in factories.items()}


def main() -> None:
    specs = _build_specs()
    merged: dict[str, object] = {"services": specs}
    with open("openapi.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(merged, f, indent=2, sort_keys=True)
        f.write("\n")
    print("OK: openapi.json generated")


if __name__ == "__main__":
    main()
