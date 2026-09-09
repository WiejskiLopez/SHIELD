"""Versioned schema migrations for the standalone User bounded context."""

from __future__ import annotations

from pathlib import Path

from shell.platform.infrastructure.persistence.alembic_runner import run_service_baseline

_MIGRATIONS_DIR = Path(__file__).resolve().parent


async def run_user_baseline(url: str, reset_db: bool = False) -> None:
    """Apply the shared platform delivery chain, then the User migration history."""
    await run_service_baseline(
        url=url,
        migrations_dir=_MIGRATIONS_DIR,
        service_package="shell.user_service",
        base_class="UserSqlAlchemyModelBase",
        reset_db=reset_db,
    )
