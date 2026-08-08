"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from bharat_os.config import get_settings


def _configure_sqlite(engine: Engine) -> None:
    """Enable foreign key enforcement on SQLite.

    SQLite ignores foreign keys unless asked, which would let the test suite
    pass while Postgres rejects the same writes in production.
    """

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
    )
    if settings.is_sqlite:
        _configure_sqlite(engine)
    return engine


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
