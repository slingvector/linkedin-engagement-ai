"""
Alembic migration environment — configured for async SQLAlchemy.

Reads DATABASE_URL from environment (must be set before running alembic commands).
All ORM models are imported here so Alembic can detect schema changes automatically.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Import Base and ALL models so autogenerate detects them ─────────────────
from app.models.base import Base  # noqa: F401

# Importing each model module registers their Tables on Base.metadata
import app.models.user          # noqa: F401
import app.models.post          # noqa: F401
import app.models.carousel      # noqa: F401
import app.models.creator       # noqa: F401
import app.models.analytics     # noqa: F401
import app.models.sales         # noqa: F401
import app.models.career        # noqa: F401
import app.models.talent        # noqa: F401
import app.models.enterprise    # noqa: F401
import app.models.llmops        # noqa: F401
import app.models.oauth_state   # noqa: F401
import app.models.user_settings  # noqa: F401

# ── Alembic Config ───────────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url from environment (takes precedence over alembic.ini)
db_url = os.getenv("DATABASE_URL", "")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode ─────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — emits SQL to stdout.
    Useful for reviewing migrations before applying them.
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


# ── Online async mode ─────────────────────────────────────────────────────────
def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (matches our asyncpg setup)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
