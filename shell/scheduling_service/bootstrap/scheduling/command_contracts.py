"""Stable wire contracts for Scheduling bounded-context delivery commands."""

from __future__ import annotations

from shell.platform.application.contracts.command_contract import CommandContract
from shell.platform.infrastructure.serialization.registries.command_registry import (
    build_command_registry,
    discover_command_types,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.provision_schedule_command import (
    ProvisionScheduleCommand,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.release_schedule_command import (
    ReleaseScheduleCommand,
)
from shell.scheduling_service.application.scheduling.scheduler_provision.commands.start_scheduler_provision_command import (
    StartSchedulerProvisionCommand,
)

SCHEDULING_COMMAND_CONTRACTS: dict[str, CommandContract] = {
    "scheduling.scheduler_provision.start": CommandContract(
        command_name="scheduling.scheduler_provision.start",
        command_class=StartSchedulerProvisionCommand,
        target_service="scheduling",
    ),
    "scheduling.scheduler_provision.provision_schedule": CommandContract(
        command_name="scheduling.scheduler_provision.provision_schedule",
        command_class=ProvisionScheduleCommand,
        target_service="scheduling",
    ),
    "scheduling.scheduler_provision.release_schedule": CommandContract(
        command_name="scheduling.scheduler_provision.release_schedule",
        command_class=ReleaseScheduleCommand,
        target_service="scheduling",
    ),
}


def build_scheduling_command_registry() -> dict[str, type]:
    """Build the local command registry and add stable delivery names."""
    registry = build_command_registry(
        discover_command_types("shell.scheduling_service.application.scheduling")
    )
    registry.update(
        {
            contract.command_name: contract.command_class
            for contract in SCHEDULING_COMMAND_CONTRACTS.values()
        }
    )
    return registry
