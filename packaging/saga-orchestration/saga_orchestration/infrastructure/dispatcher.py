from __future__ import annotations

from typing import TYPE_CHECKING

from saga_orchestration.domain.ports.outbox_writer import OutboxCommandRow

if TYPE_CHECKING:
    from saga_orchestration.domain.json_value import JsonValue
    from saga_orchestration.domain.ports.outbox_writer import CommandOutboxWriter
    from saga_orchestration.domain.step import StepDefinition


class SagaCommandDispatcher:
    """Cienki adapter: StepDefinition -> wiersz outbox. Bez sqlalchemy, bez platformy."""

    def __init__(self, writer: CommandOutboxWriter) -> None:
        self._writer = writer

    def dispatch_step(
        self,
        *,
        step: StepDefinition,
        command_id: str,
        source_service: str,
        contract_type: str,
        payload: dict[str, JsonValue],
        aggregate_id: str,
        correlation_id: str,
        causation_id: str | None,
    ) -> str:
        self._writer.append(
            OutboxCommandRow(
                command_id=command_id,
                source_service=source_service,
                destination_service=step.target_service,
                contract_type=contract_type,
                schema_version=1,
                aggregate_id=aggregate_id,
                payload=dict(payload),
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
        )
        return command_id
