"""Migrations must apply and roll back cleanly.

A migration that cannot be reversed is a migration nobody dares run in
production, so reversibility is tested rather than assumed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    "application",
    "application_window",
    "authority",
    "benefit",
    "consent_grant",
    "document_requirement",
    "eligibility_criterion",
    "outcome",
    "profile",
    "scheme",
    "scheme_version",
    "user_account",
    "user_session",
}


@pytest.fixture
def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    # Alembic stores options in a configparser, which reads '%' as interpolation
    # syntax. Postgres URLs carrying connection options are percent-encoded, so
    # the sign has to be escaped or config loading raises.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config



def test_upgrade_backfills_reviewer_flag_for_existing_accounts(
    alembic_config: Config, database_url: str
) -> None:
    command.upgrade(alembic_config, "b15f87ac2693")
    engine = create_engine(database_url)
    account_id = uuid.uuid4()

    metadata = sa.MetaData()
    account_before = sa.Table("user_account", metadata, autoload_with=engine)
    with engine.begin() as connection:
        connection.execute(
            account_before.insert().values(
                id=account_id,
                email="existing@example.com",
                password_hash=None,
                is_active=True,
                created_at=datetime.now(UTC),
            )
        )

    command.upgrade(alembic_config, "head")

    metadata = sa.MetaData()
    account_after = sa.Table("user_account", metadata, autoload_with=engine)
    with engine.connect() as connection:
        is_reviewer = connection.scalar(
            sa.select(account_after.c.is_reviewer).where(account_after.c.id == account_id)
        )
    assert is_reviewer is False

def test_upgrade_creates_every_expected_table(alembic_config: Config, database_url: str) -> None:
    command.upgrade(alembic_config, "head")
    tables = set(inspect(create_engine(database_url)).get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"migration did not create: {sorted(missing)}"


def test_downgrade_removes_every_table(alembic_config: Config, database_url: str) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    tables = set(inspect(create_engine(database_url)).get_table_names())
    leftovers = EXPECTED_TABLES & tables
    assert not leftovers, f"downgrade left tables behind: {sorted(leftovers)}"


def test_migrations_match_orm_metadata(alembic_config: Config, database_url: str) -> None:
    """The migration history must fully describe the ORM models.

    Catches the common failure where a model changes but no migration is
    generated, so tests pass locally against ``create_all`` and production
    breaks.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from bharat_os.models import Base

    command.upgrade(alembic_config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = compare_metadata(context, Base.metadata)
    assert diff == [], f"ORM models drifted from migrations: {diff}"
