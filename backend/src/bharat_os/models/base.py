"""Declarative base and shared column conventions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TypeVar

from sqlalchemy import DateTime, Enum, MetaData, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit constraint naming so Alembic can autogenerate reversible migrations
# on SQLite, which otherwise produces unnamed constraints it cannot drop.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone-aware current time. Used instead of ``datetime.utcnow``."""
    return datetime.now(UTC)


def uuid_pk() -> Mapped[uuid.UUID]:
    """Primary key column portable across SQLite and Postgres."""
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def created_at_column() -> Mapped[datetime]:
    """Creation timestamp, defaulted in Python rather than by the database.

    A ``server_default`` would be compiled by whichever engine generated the
    migration — ``now()`` on Postgres, ``CURRENT_TIMESTAMP`` on SQLite — and baked
    into the migration file, which then fails on the other engine. Defaulting in
    Python keeps migrations portable and guarantees a timezone-aware UTC value
    regardless of how the database is configured.
    """
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )


def updated_at_column() -> Mapped[datetime]:
    """Last-modified timestamp, maintained in Python for the same reason."""
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


_E = TypeVar("_E", bound=StrEnum)


def enum_column(enum_type: type[_E], constraint_name: str) -> Enum:
    """Persist a :class:`StrEnum` as ``VARCHAR`` plus a ``CHECK`` constraint.

    Native database enums are avoided because altering them differs between
    SQLite and Postgres; a check constraint behaves identically on both.
    """
    return Enum(
        enum_type,
        native_enum=False,
        values_callable=lambda e: [member.value for member in e],
        name=constraint_name,
        validate_strings=True,
    )
