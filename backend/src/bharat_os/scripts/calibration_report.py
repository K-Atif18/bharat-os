"""Print a calibration report.

    python -m bharat_os.scripts.calibration_report            # synthetic fixtures
    python -m bharat_os.scripts.calibration_report --real      # recorded outcomes

The answer to "how do we know the percentage means anything". Run it in CI so a
change that quietly degrades calibration shows up as a number rather than as user
complaints months later.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select

from bharat_os.services.calibration import CalibrationCase, measure

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "calibration_cases.json"


def load_fixture_cases() -> list[CalibrationCase]:
    payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return [CalibrationCase(**case) for case in payload["cases"]]


def load_real_cases() -> list[CalibrationCase]:
    """Build cases from recorded outcomes.

    Empty until applications have completed, which is the honest state of affairs
    rather than something to paper over.
    """
    from bharat_os.db import get_session_factory
    from bharat_os.models.application import Application, Outcome

    with get_session_factory()() as session:
        rows = session.execute(
            select(Outcome, Application).join(Application, Outcome.application_id == Application.id)
        ).all()

    cases: list[CalibrationCase] = []
    for outcome, application in rows:
        # Confidence at the time of submission is not yet persisted alongside the
        # application; that link would need to be added to the Application model.
        recorded = getattr(application, "confidence_at_submission", None)
        if recorded is None:
            continue
        cases.append(
            CalibrationCase(
                predicted_confidence=recorded,
                succeeded=outcome.outcome_type.value in {"approved", "partially_approved"},
                label=str(application.scheme_version_id),
            )
        )
    return cases


def main(argv: list[str]) -> int:
    use_real = "--real" in argv

    if use_real:
        cases = load_real_cases()
        if not cases:
            print(
                "No recorded outcomes with a stored confidence yet.\n"
                "Calibration against real data becomes meaningful once applications\n"
                "have been submitted and their results captured. Run without --real to\n"
                "exercise the harness against synthetic fixtures."
            )
            return 0
        source = "recorded application outcomes"
    else:
        cases = load_fixture_cases()
        source = "SYNTHETIC fixtures — proves the harness works, not that the system is calibrated"

    report = measure(cases)
    print(f"Source: {source}\n")
    print(report.render())
    print()
    print("Within tolerance" if report.is_within_tolerance else "OUT OF TOLERANCE")
    return 0 if report.is_within_tolerance else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
