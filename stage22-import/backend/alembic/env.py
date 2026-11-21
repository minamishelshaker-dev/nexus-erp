"""Alembic environment configured for the application's async SQLAlchemy engine."""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401 - populate Base.metadata before Alembic configures it

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    configure_options = {
        "connection": connection,
        "target_metadata": target_metadata,
        "compare_type": True,
    }

    # Diagnostic mode: generate CREATE TABLE operations only for ORM tables
    # absent from the disposable database. Never emit drops or alterations
    # against existing tables while preparing the missing-table inventory.
    if os.getenv("ALEMBIC_CREATE_MISSING_TABLES_ONLY") == "1":
        from sqlalchemy import inspect

        existing_tables = set(inspect(connection).get_table_names(schema="public"))
        missing_tables = set(target_metadata.tables) - existing_tables

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name in missing_tables and not reflected
            parent_table = getattr(obj, "table", None)
            if parent_table is not None:
                return parent_table.name in missing_tables
            return True

        configure_options["include_object"] = include_object

    context.configure(**configure_options)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        do_run_migrations(supplied_connection)
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
