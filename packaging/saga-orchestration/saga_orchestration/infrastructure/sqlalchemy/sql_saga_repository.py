from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from saga_orchestration.domain.errors import SagaGuardError, SagaVersionConflictError
from saga_orchestration.domain.saga import Saga
from saga_orchestration.domain.saga_id import SagaId
from saga_orchestration.domain.saga_key import SagaKey
from saga_orchestration.domain.saga_payload import SagaPayload
from saga_orchestration.domain.saga_status import SagaStatus
from saga_orchestration.domain.saga_version import SagaVersion
from saga_orchestration.domain.step_attempt import StepAttempt
from saga_orchestration.domain.step_name import StepName
from saga_orchestration.infrastructure.sqlalchemy.saga_models import (
    SagaInstanceRow,
    affected_rows,
    ensure_aware,
    require_aware,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncSession

    from saga_orchestration.domain.processed_delivery import DeliveryId, ProcessedDelivery
    from saga_orchestration.domain.step import StepRegistry
    from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels


class SqlSagaRepository:
    """Persystencja instancji + dziennika. Sesja wstrzyknięta, brak commitów."""

    def __init__(
        self,
        session: AsyncSession,
        models: SagaModels,
        registries: Mapping[str, StepRegistry],
    ) -> None:
        self._session = session
        self._models = models
        self._registries = registries

    async def get_by_key(self, key: SagaKey) -> Saga | None:
        row = (
            await self._session.execute(
                select(self._models.instance)
                .where(
                    self._models.instance.saga_type == key.saga_type,
                    self._models.instance.saga_key == key.business_key,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def create(self, saga: Saga) -> bool:
        """INSERT ... ON CONFLICT DO NOTHING (PG i SQLite jak w inbox platformy).

        True = nowy wiersz. False = wyścig (drugi starter reloaduje w tej samej
        transakcji). Bez savepointów: savepoint otwierający implicit transakcję
        commituje się na pysqlite przy RELEASE — cicha utrata atomowości.
        """
        result = await self._session.execute(
            pg_insert(self._models.instance)
            .values(
                id=saga.id.value,
                saga_type=saga.key.saga_type,
                saga_key=saga.key.business_key,
                status=saga.status.value,
                current_step=saga.current_step.value if saga.current_step else None,
                business_payload=dict(saga.payload.data),
                completed_steps=[step.value for step in saga.completed_steps],
                failed_steps=[step.value for step in saga.failed_steps],
                compensation_stack=[step.value for step in saga.compensation_stack],
                compensation_cursor=saga.compensation_cursor,
                attempts=[
                    {"step": record.step.value, "attempt": record.attempt}
                    for record in saga.attempts
                ],
                version=saga.version.value,
                created_at=saga.created_at,
                updated_at=saga.updated_at,
                completed_at=saga.completed_at,
                failed_at=saga.failed_at,
                compensated_at=saga.compensated_at,
            )
            .on_conflict_do_nothing(index_elements=["saga_type", "saga_key"])
        )
        return affected_rows(result) == 1

    async def store(self, saga: Saga, *, persisted_version: SagaVersion) -> None:
        result = await self._session.execute(
            update(self._models.instance)
            .where(
                self._models.instance.id == saga.id.value,
                self._models.instance.version == persisted_version.value,
            )
            .values(
                status=saga.status.value,
                current_step=saga.current_step.value if saga.current_step else None,
                business_payload=dict(saga.payload.data),
                completed_steps=[step.value for step in saga.completed_steps],
                failed_steps=[step.value for step in saga.failed_steps],
                compensation_stack=[step.value for step in saga.compensation_stack],
                compensation_cursor=saga.compensation_cursor,
                attempts=[
                    {"step": record.step.value, "attempt": record.attempt}
                    for record in saga.attempts
                ],
                version=saga.version.value,
                updated_at=saga.updated_at,
                completed_at=saga.completed_at,
                failed_at=saga.failed_at,
                compensated_at=saga.compensated_at,
            )
        )
        if affected_rows(result) != 1:
            raise SagaVersionConflictError(
                f"saga {saga.id.value} zmieniła się (oczekiwano v{persisted_version.value})"
            )

    async def is_delivery_processed(self, saga_id: SagaId, delivery_id: DeliveryId) -> bool:
        row = await self._session.get(self._models.delivery, delivery_id.value)
        return row is not None and bool(row.saga_id == saga_id.value)

    async def try_record_delivery(self, entry: ProcessedDelivery) -> bool:
        result = await self._session.execute(
            pg_insert(self._models.delivery)
            .values(
                delivery_id=entry.delivery_id.value,
                saga_id=entry.saga_id.value,
                step=entry.step.value,
                attempt=entry.attempt,
                succeeded=entry.succeeded,
                processed_at=entry.processed_at,
            )
            .on_conflict_do_nothing(index_elements=["delivery_id"])
        )
        await self._session.flush()
        return affected_rows(result) == 1

    def _to_domain(self, row: SagaInstanceRow) -> Saga:
        registry = self._registries.get(row.saga_type)
        if registry is None:
            raise SagaGuardError(f"nieznany saga_type w wierszu: {row.saga_type!r}")
        status = self._parse_status(row.status)
        current = StepName(row.current_step) if row.current_step else None
        return Saga.restore(
            saga_id=SagaId(row.id),
            key=SagaKey(saga_type=row.saga_type, business_key=row.saga_key),
            payload=SagaPayload(dict(row.business_payload or {})),
            steps=registry,
            status=status,
            current_step=current,
            completed=tuple(StepName(name) for name in (row.completed_steps or [])),
            failed=tuple(StepName(name) for name in (row.failed_steps or [])),
            compensation_stack=tuple(StepName(name) for name in (row.compensation_stack or [])),
            compensation_cursor=int(row.compensation_cursor or 0),
            attempts=tuple(
                StepAttempt(step=StepName(item["step"]), attempt=int(item["attempt"]))
                for item in (row.attempts or [])
            ),
            version=SagaVersion(int(row.version)),
            created_at=require_aware(row.created_at, "created_at"),
            updated_at=require_aware(row.updated_at, "updated_at"),
            completed_at=ensure_aware(row.completed_at),
            failed_at=ensure_aware(row.failed_at),
            compensated_at=ensure_aware(row.compensated_at),
        )

    def _parse_status(self, raw: str) -> SagaStatus:
        try:
            return SagaStatus(raw)
        except ValueError as exc:
            raise SagaGuardError(f"nieznany status sagi w bazie: {raw!r}") from exc
