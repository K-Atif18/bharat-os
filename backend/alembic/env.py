"""Alembic environment.

The database URL comes from :mod:`bharat_os.config` rather than ``alembic.ini``
so migrations and the application can never disagree about which database they
are talking to, and no credentials are committed.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from bharat_os.config import get_settings
from bharat_os.models import Base  # noqa: F401 - imports every model

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
# configparser treats '%' as interpolation syntax, and Postgres URLs carrying
# connection options are percent-encoded, so the sign must be escaped here.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

target_metadata = Base.metadata

# SQLite cannot ALTER most constructs in place; batch mode rewrites the table
# instead. Harmless on Postgres, essential locally.
RENDER_AS_BATCH = settings.is_sqlite


def render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    """Render the encrypted column types as their underlying ``TEXT`` impl.

    ``EncryptedText`` and ``EncryptedInt`` are application-level concerns: they
    decide how a value is encoded before it reaches the database. The DDL they
    produce is plain ``TEXT``. Rendering them literally would make every
    migration import application code, coupling the migration history to code
    that will keep changing underneath it.
    """
    from bharat_os.crypto import EncryptedInt, EncryptedText

    if type_ == "type" and isinstance(obj, EncryptedText | EncryptedInt):
        return "sa.Text()"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=RENDER_AS_BATCH,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=RENDER_AS_BATCH,
            compare_type=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
