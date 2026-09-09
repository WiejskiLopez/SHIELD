"""Versioned schema migrations for the Session bounded context."""

from __future__ import annotations

from pathlib import Path

from shell.platform.infrastructure.persistence.alembic_runner import run_service_baseline

_MIGRATIONS_DIR = Path(__file__).resolve().parent


async def run_session_baseline(url: str, reset_db: bool = False) -> None:
    """Apply the shared platform delivery chain, then the Session migration history."""
    await run_service_baseline(
        url=url,
        migrations_dir=_MIGRATIONS_DIR,
        service_package="shell.session_service",
        base_class="SessionSqlAlchemyModelBase",
        reset_db=reset_db,
    )
