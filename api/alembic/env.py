"""
Alembic migration environment for AuditCaseOS.

This module configures Alembic to work with async SQLAlchemy and pgvector.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object - provides access to .ini file values
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models for autogenerate support
# This imports the Base class with all model metadata
from app.models import Base

# Import pgvector for type registration
try:
    import pgvector.sqlalchemy
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

# Target metadata for autogenerate
target_metadata = Base.metadata

# Get database URL from environment (set by Docker Compose)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://auditcaseos:auditcaseos_secret@localhost:15432/auditcaseos"
)

# Override sqlalchemy.url with environment variable
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This generates SQL scripts without connecting to the database.
    Useful for generating migration SQL for review or manual application.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations with an active database connection.

    This is called within the async context to execute migrations.
    """
    # Register pgvector type with PostgreSQL dialect for autogenerate
    if HAS_PGVECTOR:
        connection.dialect.ischema_names["vector"] = pgvector.sqlalchemy.Vector

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Create async engine and run migrations.

    Uses NullPool to avoid connection pooling issues during migrations.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    This connects to the database and applies migrations directly.
    """
    asyncio.run(run_async_migrations())


# Determine mode and run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
