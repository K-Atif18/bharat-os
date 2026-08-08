"""Liveness and readiness reporting."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from bharat_os.config import get_settings
from bharat_os.db import get_db

router = APIRouter(tags=["system"])

DbSession = Annotated[Session, Depends(get_db)]


class LivenessOut(BaseModel):
    status: Literal["ok"]


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    database: Literal["reachable", "unreachable"]
    scheme_count: int | None = None


@router.get("/health/live", response_model=LivenessOut)
def liveness() -> LivenessOut:
    """Report only whether the API process can serve requests.

    This deliberately has no database dependency, so an orchestrator does not
    restart a healthy process merely because a downstream service is unavailable.
    """
    return LivenessOut(status="ok")


def _readiness(response: Response, db: Session) -> HealthOut:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        scheme_count = db.execute(text("SELECT COUNT(*) FROM scheme")).scalar_one()
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthOut(
            status="degraded",
            environment=settings.environment,
            database="unreachable",
        )
    return HealthOut(
        status="ok",
        environment=settings.environment,
        database="reachable",
        scheme_count=int(scheme_count),
    )


@router.get("/health/ready", response_model=HealthOut)
def readiness(response: Response, db: DbSession) -> HealthOut:
    """Report whether dependencies required to serve application traffic work."""
    return _readiness(response, db)


@router.get("/health", response_model=HealthOut)
def health(response: Response, db: DbSession) -> HealthOut:
    """Backward-compatible readiness endpoint for existing deployments."""
    return _readiness(response, db)
