"""Shared test fixtures.

Tests run against whichever database ``BHARAT_OS_TEST_DATABASE_URL`` names,
defaulting to Postgres — the production engine. Running the suite against a
different engine than production is how a Postgres-incompatible migration
reaches production unnoticed.

Isolation strategy differs by engine:

* **Postgres** — each test gets its own schema, created and dropped around the
  test. Cheap, parallel-safe, and exercises the real engine.
* **SQLite** — each test gets its own file, for contributors without a local
  Postgres.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

# Configure the environment before any application module is imported, since
# settings are cached on first use.
os.environ.setdefault("BHARAT_OS_ENVIRONMENT", "test")
os.environ.setdefault("BHARAT_OS_ENCRYPTION_KEY", "Zh3rVJ0dQ8pQ0Z1kX2wA9sT4nR6uY8bC1dE3fG5hI7k=")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from bharat_os import config, db  # noqa: E402

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg:///bharat_os"


def _base_url() -> str:
    return os.environ.get("BHARAT_OS_TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def _reset_caches() -> None:
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_session_factory.cache_clear()


def _postgres_reachable(url: str) -> bool:
    try:
        with create_engine(url).connect():
            return True
    except OperationalError:
        return False


@pytest.fixture(scope="session")
def base_database_url() -> str:
    """The configured test database, skipping the suite if Postgres is absent."""
    url = _base_url()
    if url.startswith("sqlite"):
        return url
    if not _postgres_reachable(url):
        pytest.skip(
            f"Postgres not reachable at {url}. Start it, or set "
            "BHARAT_OS_TEST_DATABASE_URL=sqlite:///./test.db"
        )
    return url


@pytest.fixture
def database_url(base_database_url: str, tmp_path: Path) -> Iterator[str]:
    """Point the application at an isolated database for one test."""
    if base_database_url.startswith("sqlite"):
        url = f"sqlite:///{tmp_path / 'test.db'}"
        schema: str | None = None
    else:
        # A per-test schema keeps tests independent without the cost of
        # creating a database per test.
        schema = f"test_{uuid.uuid4().hex[:12]}"
        url = f"{base_database_url}?options=-csearch_path%3D{schema}"

    previous = os.environ.get("BHARAT_OS_DATABASE_URL")
    os.environ["BHARAT_OS_DATABASE_URL"] = url
    _reset_caches()

    if schema is not None:
        with create_engine(base_database_url).connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.commit()

    try:
        yield url
    finally:
        db.get_engine.cache_clear()
        if schema is not None:
            with create_engine(base_database_url).connect() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
                connection.commit()
        if previous is None:
            os.environ.pop("BHARAT_OS_DATABASE_URL", None)
        else:
            os.environ["BHARAT_OS_DATABASE_URL"] = previous
        _reset_caches()


@pytest.fixture
def engine(database_url: str) -> Engine:
    """An engine with the full schema created from ORM metadata."""
    from bharat_os.models import Base

    eng = db.get_engine()
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = db.get_session_factory()
    with factory() as s:
        yield s


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    """An API client bound to the per-test database."""
    from bharat_os.main import create_app
    from bharat_os.rate_limit import reset_rate_limits

    # The rate limiter is process-global state (see bharat_os.rate_limit), so
    # without a reset here one test's requests would count against the next
    # test's budget and produce unrelated 429s.
    reset_rate_limits()
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def seeded_corpus(engine: Engine) -> int:
    """Load the real curated corpus into the per-test database.

    Tests that exercise ranking and matching run against the actual scheme data
    rather than fixtures, so a change to a curated rule that breaks matching shows
    up here instead of in production.
    """
    from bharat_os.seed.loader import load_from_disk

    factory = db.get_session_factory()
    with factory() as session:
        report = load_from_disk(session)
    return report.schemes_created
