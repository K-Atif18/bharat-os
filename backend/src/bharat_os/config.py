"""Application configuration, loaded from the environment.

Every setting is prefixed ``BHARAT_OS_`` so the backend cannot accidentally
pick up unrelated environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root, i.e. the directory containing backend/ and frontend/.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration.

    Defaults are development-friendly. Production safety is enforced by
    :meth:`validate_production_requirements`, which is called at app startup.
    """

    model_config = SettingsConfigDict(
        env_prefix="BHARAT_OS_",
        env_file=(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"

    # Postgres is the production engine and the development default. SQLite is
    # supported as a fallback for contributors without a local Postgres, but is
    # rejected in production.
    database_url: str = "postgresql+psycopg:///bharat_os"

    # Fernet key protecting sensitive profile fields at rest. Optional in
    # development (a per-process ephemeral key is generated), mandatory in
    # production.
    encryption_key: str = ""

    # Scheme criteria not re-verified within this window are surfaced to the
    # user as potentially stale rather than silently trusted.
    staleness_threshold_days: int = Field(default=90, ge=1)

    #: Browser origins permitted to call the API, comma-separated.
    #:
    #: Explicit rather than permissive: credentials are sent with every request,
    #: so a wildcard origin would let any site act as a signed-in user.
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM provider settings. ``mock`` performs no network calls.
    llm_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"

    #: Optional error tracking. Left blank, tracking is simply not initialised —
    #: this is observability, not a required dependency.
    sentry_dsn: str = ""

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("database_url must not be empty")
        # Managed platforms (Railway, Render, Heroku) expose their Postgres
        # connection string as ``postgres://`` or ``postgresql://``, which
        # SQLAlchemy resolves to the psycopg2 driver. This project ships
        # psycopg v3, so normalise the scheme to ``postgresql+psycopg://``.
        # This lets a platform's own DATABASE_URL be used verbatim, without a
        # hand-edited driver prefix that is easy to get wrong.
        normalised = value.strip()
        if normalised.startswith("postgres://"):
            normalised = "postgresql://" + normalised[len("postgres://") :]
        if normalised.startswith("postgresql://"):
            normalised = "postgresql+psycopg://" + normalised[len("postgresql://") :]
        return normalised

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def validate_production_requirements(self) -> None:
        """Fail fast on configuration that is unsafe outside development."""
        if self.environment != "production":
            return
        problems = []
        if not self.encryption_key:
            problems.append(
                "BHARAT_OS_ENCRYPTION_KEY is required in production; sensitive "
                "profile fields cannot be stored without it"
            )
        if self.is_sqlite:
            problems.append(
                "SQLite is not supported in production; set BHARAT_OS_DATABASE_URL "
                "to a Postgres URL"
            )
        if problems:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
