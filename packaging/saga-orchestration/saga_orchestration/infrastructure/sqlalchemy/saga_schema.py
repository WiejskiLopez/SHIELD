from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from saga_orchestration.infrastructure.sqlalchemy.saga_models import SagaModels


def upgrade_saga_schema(bind: Connection, models: SagaModels) -> None:
    """Jedno źródło DDL: tabele wprost z modeli libki.

    Wołane PRZEZ migrację adopcyjną serwisu (RFC-06) jako
    ``upgrade_saga_schema(op.get_bind(), SAGA_MODELS)``. Deterministyczne,
    bez IF NOT EXISTS. Bind (nie proxy `op`), bo `alembic.op` to moduł,
    nie instancja Operations.
    """
    models.delivery.__table__.create(bind, checkfirst=False)
    models.instance.__table__.create(bind, checkfirst=False)
    models.timeout.__table__.create(bind, checkfirst=False)


def downgrade_saga_schema(bind: Connection, models: SagaModels) -> None:
    models.timeout.__table__.drop(bind, checkfirst=False)
    models.instance.__table__.drop(bind, checkfirst=False)
    models.delivery.__table__.drop(bind, checkfirst=False)
