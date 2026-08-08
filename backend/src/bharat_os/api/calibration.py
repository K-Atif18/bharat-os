"""Live confidence calibration reporting.

``services/calibration.py`` measures whether stated confidence scores mean
what they claim, but until now that measurement was only runnable as a CLI
script (``scripts/calibration_report.py``). This module exposes the same
measurement as an API endpoint so it is visible without a terminal.

Real calibration requires real outcomes, and the outcome table is empty by
design until applications complete — recording a confidence score at the
moment a user submits an application is not implemented yet (see
``scripts/calibration_report.py``'s ``load_real_cases``, which already
documents this: ``Application`` has no ``confidence_at_submission`` field to
join against). Rather than inventing an approximate join to make this
endpoint report something, it reuses exactly the same logic the CLI script
uses: real cases if the schema ever supports them, synthetic fixtures
otherwise, always labelled honestly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import pydantic
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.db import get_db
from bharat_os.models.application import Application, Outcome
from bharat_os.services.calibration import CalibrationCase, measure

router = APIRouter(prefix="/calibration", tags=["calibration"])

DbSession = Annotated[Session, Depends(get_db)]

FIXTURES_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "calibration_cases.json"
)

SYNTHETIC_WARNING = (
    "Calibration is based on synthetic fixture data, not real application "
    "outcomes. It proves the measurement works, not that Bharat OS is "
    "calibrated. Once real applications complete and their outcomes are "
    "recorded, the same measurement will run against them and mean "
    "something about the system rather than about this fixture."
)


class BucketOut(pydantic.BaseModel):
    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_rate: float
    gap: float
    direction: str


class CalibrationOut(pydantic.BaseModel):
    expected_calibration_error: float | None
    max_calibration_error: float | None
    sample_size: int
    base_rate: float | None
    overall_direction: str | None
    buckets: list[BucketOut]
    has_real_outcomes: bool
    warning: str | None


def _load_fixture_cases() -> list[CalibrationCase]:
    if not FIXTURES_PATH.exists():
        return []
    payload = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return [CalibrationCase(**case) for case in payload["cases"]]


def _load_real_cases(db: Session) -> list[CalibrationCase]:
    """Real cases, if the schema ever supports recording predicted confidence
    at the moment of submission. Empty today, by design - see module
    docstring. Left as a real query rather than a stub so this starts
    returning real data the day ``Application`` gains that field, with no
    other change needed here.
    """
    rows = db.execute(
        select(Outcome, Application).join(Application, Outcome.application_id == Application.id)
    ).all()

    cases: list[CalibrationCase] = []
    for outcome, application in rows:
        recorded_confidence = getattr(application, "confidence_at_submission", None)
        if recorded_confidence is None:
            continue
        cases.append(
            CalibrationCase(
                predicted_confidence=recorded_confidence,
                succeeded=outcome.outcome_type.value in {"approved", "partially_approved"},
                label=str(application.scheme_version_id),
            )
        )
    return cases


@router.get("/", response_model=CalibrationOut)
def get_calibration(db: DbSession) -> CalibrationOut:
    """Calibration report: real outcomes if any exist, synthetic fixtures
    otherwise. The response always says which one it is - a caller must
    never be able to mistake a demo number for a real one.
    """
    real_cases = _load_real_cases(db)
    has_real = len(real_cases) > 0
    cases = real_cases if has_real else _load_fixture_cases()

    if not cases:
        return CalibrationOut(
            expected_calibration_error=None,
            max_calibration_error=None,
            sample_size=0,
            base_rate=None,
            overall_direction=None,
            buckets=[],
            has_real_outcomes=False,
            warning="No calibration data available.",
        )

    report = measure(cases)

    return CalibrationOut(
        expected_calibration_error=round(report.expected_calibration_error, 4),
        max_calibration_error=round(report.max_calibration_error, 4),
        sample_size=report.sample_size,
        base_rate=round(report.base_rate, 4),
        overall_direction=report.overall_direction,
        buckets=[
            BucketOut(
                lower=bucket.lower,
                upper=bucket.upper,
                count=bucket.count,
                mean_predicted=round(bucket.mean_predicted, 4),
                observed_rate=round(bucket.observed_rate, 4),
                gap=round(bucket.gap, 4),
                direction=bucket.direction,
            )
            for bucket in report.buckets
        ],
        has_real_outcomes=has_real,
        warning=None if has_real else SYNTHETIC_WARNING,
    )
