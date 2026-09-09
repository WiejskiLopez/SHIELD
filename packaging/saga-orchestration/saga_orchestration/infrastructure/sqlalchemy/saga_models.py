from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from saga_orchestration.domain.errors import SagaGuardError

if TYPE_CHECKING:
    from sqlalchemy.engine import Result


def affected_rows(result: Result[Any]) -> int:
    """rowcount dla DML zbudowanego na dynamicznych modelach (Result[Any])."""
    return int(getattr(result, "rowcount", 0) or 0)


def ensure_aware(value: datetime | None) -> datetime | None:
    """SQLite gubi strefę czasową; reszta stosu wymaga aware UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def require_aware(value: datetime | None, field: str) -> datetime:
    """Kolumna NOT NULL: None oznacza korupcję danych, nie brak."""
    aware = ensure_aware(value)
    if aware is None:
        raise SagaGuardError(f"wiersz sagi bez wymaganego pola: {field}")
    return aware


class SagaInstanceRow(Protocol):
    """Kształt wiersza saga_instance do odczytu (modele są dynamiczne)."""

    id: str
    saga_type: str
    saga_key: str
    status: str
    current_step: str | None
    business_payload: dict[str, Any]
    completed_steps: list[str]
    failed_steps: list[str]
    compensation_stack: list[str]
    compensation_cursor: int
    attempts: list[dict[str, Any]]
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    failed_at: datetime | None
    compensated_at: datetime | None


class SagaTimeoutRow(Protocol):
    """Kształt wiersza saga_timeout do odczytu."""

    id: str
    saga_id: str
    saga_type: str
    saga_key: str
    step: str
    attempt: int
    kind: str
    due_at: datetime
    status: str
    owner: str | None
    lease_until: datetime | None
    correlation_id: str
    causation_id: str | None


class SagaDeliveryRow(Protocol):
    """Kształt wiersza saga_processed_delivery do odczytu."""

    delivery_id: str
    saga_id: str


@dataclass(frozen=True, slots=True)
class SagaModels:
    """Trzy tabele sagi zbudowane na Base SERWISU (jego MetaData, jego łańcuch migracji)."""

    instance: type[Any]
    timeout: type[Any]
    delivery: type[Any]


def build_saga_models(base: type[DeclarativeBase]) -> SagaModels:
    class SagaInstanceModel(base):  # type: ignore[misc, valid-type]
        __tablename__ = "saga_instance"
        __table_args__ = (
            UniqueConstraint("saga_type", "saga_key", name="uq_saga_instance_type_key"),
            Index("ix_saga_instance_status_current", "status", "current_step"),
        )

        id: Mapped[str] = mapped_column(String(64), primary_key=True)
        saga_type: Mapped[str] = mapped_column(String(128), nullable=False)
        saga_key: Mapped[str] = mapped_column(String(256), nullable=False)
        status: Mapped[str] = mapped_column(String(32), nullable=False)
        current_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
        business_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
        completed_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
        failed_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
        compensation_stack: Mapped[list[str]] = mapped_column(JSON, default=list)
        compensation_cursor: Mapped[int] = mapped_column(Integer, default=0)
        attempts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
        version: Mapped[int] = mapped_column(Integer, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
        completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
        failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
        compensated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    class SagaTimeoutModel(base):  # type: ignore[misc, valid-type]
        __tablename__ = "saga_timeout"
        __table_args__ = (Index("ix_saga_timeout_status_due", "status", "due_at"),)

        id: Mapped[str] = mapped_column(String(64), primary_key=True)
        saga_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
        saga_type: Mapped[str] = mapped_column(String(128), nullable=False)
        saga_key: Mapped[str] = mapped_column(String(256), nullable=False)
        step: Mapped[str] = mapped_column(String(128), nullable=False)
        attempt: Mapped[int] = mapped_column(Integer, nullable=False)
        kind: Mapped[str] = mapped_column(String(32), nullable=False)
        due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
        status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
        owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
        lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
        correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
        causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    class SagaDeliveryModel(base):  # type: ignore[misc, valid-type]
        __tablename__ = "saga_processed_delivery"

        delivery_id: Mapped[str] = mapped_column(String(128), primary_key=True)
        saga_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
        step: Mapped[str] = mapped_column(String(128), nullable=False)
        attempt: Mapped[int] = mapped_column(Integer, nullable=False)
        succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
        processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    return SagaModels(
        instance=SagaInstanceModel, timeout=SagaTimeoutModel, delivery=SagaDeliveryModel
    )
