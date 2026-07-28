"""Alembic environment configuration script."""

# pylint: disable=no-member, wrong-import-position

# isort: off

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── 1. MUST BE AT THE VERY TOP BEFORE ANY 'app' IMPORTS ──────────────
# Use this file's own location rather than os.getcwd(), so it still works
# no matter which directory `alembic` / `task mm` is invoked from.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.database.base import Base

import app.models  # noqa: F401 # pylint: disable=unused-import # pyright: ignore[reportUnusedImport]

# isort: on

# This is the Alembic Config object
config = context.config

# ── 2. DYNAMICALLY INJECT YOUR DATABASE URL ─────────────────────────
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations offline."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations online."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
