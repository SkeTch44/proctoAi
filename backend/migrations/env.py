"""
Alembic environment configuration.

Supports both SQLite (dev) and PostgreSQL (prod) via DATABASE_URL.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Add backend to path so models can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models_sa import Base  # noqa: E402

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    """Get database URL from environment or alembic.ini."""
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    # Handle sqlite:/// prefix
    if url and url.startswith("sqlite:///"):
        return url
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
