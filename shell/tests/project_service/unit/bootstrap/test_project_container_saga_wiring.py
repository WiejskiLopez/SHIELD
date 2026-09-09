from __future__ import annotations

from shell.project_service.application.project.project_provision.commands.provision_workspace_command import (
    ProvisionWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.commands.release_workspace_command import (
    ReleaseWorkspaceCommand,
)
from shell.project_service.application.project.project_provision.commands.start_project_provision_command import (
    StartProjectProvisionCommand,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provision_failed_integration_event import (
    WorkspaceProvisionFailedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_provisioned_integration_event import (
    WorkspaceProvisionedIntegrationEvent,
)
from shell.project_service.application.project.project_provision.integration_events.workspace_released_integration_event import (
    WorkspaceReleasedIntegrationEvent,
)
from shell.project_service.bootstrap.project.command_contracts import PROJECT_COMMAND_CONTRACTS
from shell.project_service.bootstrap.project.container.project_core_container import (
    ProjectCoreContainer,
    configure_project_container,
)
from shell.project_service.process.project.project_provision.handlers.provision_result_bridge_handler import (
    ProvisionResultBridgeHandler,
)
from shell.project_service.process.project.project_provision.handlers.release_result_bridge_handler import (
    ReleaseResultBridgeHandler,
)
from shell.project_service.process.project.project_provision.handlers.start_saga_bridge_handler import (
    StartProjectProvisionBridgeHandler,
)


def test_project_container_registers_saga_roles() -> None:
    container = ProjectCoreContainer()

    configure_project_container(container)

    command_handlers = container.command_bus()._handler_factories
    assert StartProjectProvisionCommand in command_handlers
    assert ProvisionWorkspaceCommand in command_handlers
    assert ReleaseWorkspaceCommand in command_handlers

    event_handlers = container.event_bus()._handler_factories
    assert WorkspaceProvisionedIntegrationEvent in event_handlers
    assert WorkspaceProvisionFailedIntegrationEvent in event_handlers
    assert WorkspaceReleasedIntegrationEvent in event_handlers

    assert set(PROJECT_COMMAND_CONTRACTS) == {
        "project.project_provision.start",
        "project.project_provision.provision_workspace",
        "project.project_provision.release_workspace",
    }


def test_project_container_wires_saga_through_install() -> None:
    container = ProjectCoreContainer()
    container.config.db_url.from_value("sqlite+aiosqlite:///:memory:")
    container.config.broker_url.from_value("amqp://localhost")

    configure_project_container(container)

    wiring = container.saga_wiring()
    assert wiring.start_handler is not None
    assert wiring.advance_handler is not None
    assert wiring.timeout_handler is not None
    assert wiring.timeout_worker is not None

    start_bridge = container.start_saga_bridge_handler_factory()
    assert isinstance(start_bridge, StartProjectProvisionBridgeHandler)
    provision_bridge = container.provision_result_bridge_handler_factory()
    assert isinstance(provision_bridge, ProvisionResultBridgeHandler)
    release_bridge = container.release_result_bridge_handler_factory()
    assert isinstance(release_bridge, ReleaseResultBridgeHandler)

    worker = container.saga_timeout_worker_factory()
    assert worker is wiring.timeout_worker

    probes = container.readiness_probe()._probes
    assert len(probes) == 3
