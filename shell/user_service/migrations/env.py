from __future__ import annotations

import importlib
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

service_package = "shell.user_service"
infrastructure = importlib.import_module(service_package + ".infrastructure")
infrastructure_root = Path(next(iter(infrastructure.__path__)))
for model_path in infrastructure_root.rglob("*.py"):
    if "models" not in model_path.parts or model_path.name == "__init__.py":
        continue
    relative = model_path.relative_to(infrastructure_root).with_suffix("")
    importlib.import_module(infrastructure.__name__ + "." + ".".join(relative.parts))
base_module = importlib.import_module(
    service_package + ".infrastructure.user.persistence.sql.models.base"
)
target_metadata = base_module.UserSqlAlchemyModelBase.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=context.config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        context.config.get_section(context.config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
