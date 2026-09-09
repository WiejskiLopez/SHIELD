"""Unit tests — SagaTimeoutReadinessProbe (lokalny model, bez saga-orchestration)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from sqlalchemy import DateTime, String
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from shell.platform.observability.infrastructure.health.saga_timeout_readiness_probe import (
    SagaTimeoutReadinessProbe,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from shell.platform.observability.infrastructure.health.saga_timeout_readiness_probe import (
        SagaTimeoutReadModel,
    )


class Base(DeclarativeBase):
    pass


class TimeoutRow(Base):
    __tablename__ = "saga_timeout"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def make_probe(
    factory: async_sessionmaker[AsyncSession], max_backlog: int = 0
) -> SagaTimeoutReadinessProbe:
    return SagaTimeoutReadinessProbe(
        session_factory=factory,
        timeout_model=cast("type[SagaTimeoutReadModel]", TimeoutRow),
        max_backlog=max_backlog,
    )


class TestSagaTimeoutReadinessProbe:
    async def test_ready_when_no_overdue_rows(self) -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        report = await make_probe(factory).check()

        assert report.ready is True
        assert report.checks == {"database": True, "migrations": True, "backlog": True}
        await engine.dispose()

    async def test_not_ready_when_overdue_pending_exceeds_backlog(self) -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            session.add(
                TimeoutRow(
                    id="t-1",
                    status="pending",
                    due_at=datetime.now(tz=UTC) - timedelta(minutes=1),
                    lease_until=None,
                )
            )
            await session.commit()

        report = await make_probe(factory, max_backlog=0).check()

        assert report.ready is False
        assert report.checks["backlog"] is False
        await engine.dispose()

    async def test_ready_when_claimed_with_fresh_lease(self) -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            session.add(
                TimeoutRow(
                    id="t-2",
                    status="claimed",
                    due_at=datetime.now(tz=UTC) - timedelta(minutes=5),
                    lease_until=datetime.now(tz=UTC) + timedelta(minutes=5),
                )
            )
            await session.commit()

        report = await make_probe(factory, max_backlog=0).check()

        assert report.ready is True
        await engine.dispose()
