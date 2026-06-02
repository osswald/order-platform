from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.database import Base
from app import models  # noqa: F401
from app import models_operational  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def _sqlite_pragmas(connection) -> None:
    if connection.dialect.name != "sqlite":
        return
    connection.execute(text("PRAGMA journal_mode=WAL"))
    connection.execute(text("PRAGMA synchronous=NORMAL"))
    connection.execute(text("PRAGMA foreign_keys=ON"))
    connection.execute(text("PRAGMA cache_size=-8192"))
    connection.execute(text("PRAGMA temp_store=MEMORY"))
    connection.execute(text("PRAGMA mmap_size=67108864"))


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _sqlite_pragmas(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
