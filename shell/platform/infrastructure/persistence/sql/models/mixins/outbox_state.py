"""OutboxStateMixin — shared operational state columns for every outbox delivery model.

Event and command outboxes share the same operational lifecycle (claim, retry
with backoff, dead letter, replay) so the columns live in one platform mixin
instead of being duplicated across models. Mirrors ``InboxStateMixin`` without
its inbox-only columns: ``published_at`` already marks a sent row, ``error``
is inbox legacy, and ``schema_version`` is declared by each outbox model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from shell.platform.domain.value_objects.outbox_status import OutboxStatus


def _default_next_attempt_at() -> datetime:
    return datetime.now(tz=UTC).replace(microsecond=0)


def build_outbox_state_indexes(table_name: str) -> tuple[Index, ...]:
    """Return the shared operational indexes for an outbox table."""
    return (
        Index(
            f"ix_{table_name}_status_next_attempt",
            "status",
            "next_attempt_at",
        ),
    )


class OutboxStateMixin:
    """Adds the shared operational lifecycle columns to an outbox model.

    The ``status`` column uses ``PENDING`` as its default so every outbox row
    starts in the same explicit state. ``next_attempt_at`` defaults to the insert
    time so the claim query never has to special-case NULL. ``published_at``
    (declared by each outbox model) stays the sent marker: a row is delivered
    exactly when ``published_at IS NOT NULL``.
    """

    @declared_attr  # type: ignore[arg-type]  # SQLAlchemy stubs expect Mapped[T]; __table_args__ returns tuple of Index
    def __table_args__(cls: type[Any]) -> tuple[Index, ...]:
        return build_outbox_state_indexes(cls.__tablename__)

    status: Mapped[str] = mapped_column(nullable=False, default=OutboxStatus.PENDING.value)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_next_attempt_at
    )
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    claimed_by: Mapped[str | None] = mapped_column(nullable=True, default=None)
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(nullable=True, default=None)
    error_message: Mapped[str | None] = mapped_column(nullable=True, default=None)
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
