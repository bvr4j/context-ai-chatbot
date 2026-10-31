import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings, normalize_database_url
from app.database import Base
from app.models import Conversation, Message  # noqa: F401 - register models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_migration_url() -> str:
    """Resolve the migration database URL.
    
    Prefers DATABASE_URL_UNPOOLED (direct non-pooled connection for Neon migrations).
    Falls back to DATABASE_URL.
    """
    # 1. Command-line override via -x url=...
    cmd_url = context.get_x_argument(as_dictionary=True).get("url")
    if cmd_url:
        return normalize_database_url(cmd_url)

    # 2. Check direct environment variable
    direct_unpooled = os.getenv("DATABASE_URL_UNPOOLED")
    if direct_unpooled and direct_unpooled.strip():
        return normalize_database_url(direct_unpooled.strip())

    # 3. Check loaded settings
    settings = get_settings()
    if settings.database_url_unpooled and settings.database_url_unpooled.strip():
        return settings.database_url_unpooled

    if settings.database_url and settings.database_url.strip():
        return settings.database_url

    return "sqlite:///./contextai.db"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_migration_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_migration_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

    connectable = create_engine(
        url,
        connect_args=connect_args,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
