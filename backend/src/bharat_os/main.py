"""Bharat OS API application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bharat_os.api import (
    applications,
    auth,
    deadlines,
    documents,
    drafts,
    freshness,
    health,
    matches,
    profile,
    review_queue,
    schemes,
)
from bharat_os.config import Settings, get_settings
from bharat_os.http_middleware import RequestContextMiddleware
from bharat_os.logging_config import configure_logging

logger = logging.getLogger(__name__)

DESCRIPTION = """
Eligibility reasoning and application execution for Indian government funding
schemes.

**This API is advisory.** It reports calibrated confidence with per-criterion
evidence; it never certifies that an applicant is eligible, and it never submits
an application on a user's behalf.
"""


def _init_error_tracking(settings: Settings) -> None:
    """Initialise Sentry if a DSN is configured.

    Imported lazily so a deployment without error tracking never needs the
    ``sentry-sdk`` package installed.
    """
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        logger.warning(
            "BHARAT_OS_SENTRY_DSN is set but sentry-sdk is not installed; "
            "error tracking is disabled. Install it with `pip install sentry-sdk`."
        )
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        # Personal data must never leave via error reports, mirroring the
        # redaction guarantee in bharat_os.logging_config.
        send_default_pii=False,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_production_requirements()
    configure_logging(environment=settings.environment)
    _init_error_tracking(settings)

    app = FastAPI(
        title="Bharat OS",
        description=DESCRIPTION,
        version="0.1.0",
    )

    # Explicit origins, never a wildcard: credentials accompany every request,
    # so a permissive origin would let any site act as a signed-in user.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(
        RequestContextMiddleware,
        production=settings.environment == "production",
    )

    app.include_router(health.router)
    app.include_router(schemes.router)
    app.include_router(freshness.router)
    app.include_router(auth.router)
    app.include_router(profile.router)
    # drafts.router must be included before matches.router: it defines
    # GET /matches/draftable, a static path, and FastAPI matches routes in
    # registration order. Included afterwards, it would never be reached because
    # matches.router's GET /matches/{slug} matches "draftable" as a slug first.
    app.include_router(drafts.router)
    app.include_router(matches.router)
    app.include_router(documents.router)
    app.include_router(deadlines.router)
    app.include_router(applications.router)
    app.include_router(review_queue.router)
    return app


app = create_app()
