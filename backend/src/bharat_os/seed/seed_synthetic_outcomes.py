"""Seed synthetic outcome data, for demo and calibration purposes only.

    python -m bharat_os.seed.seed_synthetic_outcomes

Every row inserted here has ``Outcome.notes`` prefixed with
``api.intelligence.SYNTHETIC_MARKER`` and every ``Application.user_id`` is
``None``. Neither is a real applicant's result. They exist to:

1. Make the intelligence API return something demonstrable before any real
   user has reported an outcome.
2. Provide non-empty data for the calibration harness to run against.

Idempotent: refuses to insert again if any synthetic row already exists for
a scheme, so re-running this does not keep multiplying the sample.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.api.intelligence import SYNTHETIC_MARKER
from bharat_os.models.application import Application, Outcome
from bharat_os.models.enums import OutcomeType
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.services.outcomes import turnover_band

#: Scheme slugs to seed against — must already exist after `make seed`. A
#: missing slug is skipped, not an error, since the curated corpus can
#: change independently of this file.
SCHEME_OUTCOMES: dict[str, dict] = {
    "sisfs": {
        "approved": 6,
        "rejected": 12,
        "rejection_reasons": [
            "Missing audited financials for the past two years",
            "Pitch deck did not demonstrate commercial viability",
            "Revenue exceeded the seed-stage cap at the time of application",
            "DPIIT recognition lapsed before disbursement",
        ],
        "avg_days": 87,
    },
    "pmegp": {
        "approved": 14,
        "rejected": 8,
        "rejection_reasons": [
            "Project cost exceeded the eligible limit without a revised DPR",
            "Applicant had an existing loan default on record",
            "Land ownership documents were not in the applicant's name",
        ],
        "avg_days": 120,
    },
    "cgtmse": {
        "approved": 18,
        "rejected": 7,
        "rejection_reasons": [
            "Business vintage was under the minimum required period",
            "Existing NPA classification at the lending bank",
        ],
        "avg_days": 45,
    },
}

#: Sample turnover figures spread across bands, so the by-turnover-band
#: breakdown has more than one bucket to show.
TURNOVER_SAMPLES = (500_000, 1_500_000, 8_000_000, 25_000_000, 75_000_000)

#: Fixed seed: reproducible, so the demo shows the same numbers every run
#: rather than drifting between machines.
_RNG_SEED = 42


def seed_synthetic_outcomes(db: Session) -> int:
    """Insert synthetic outcomes for the configured schemes.

    Returns the number of rows inserted, 0 if nothing was inserted because
    synthetic data already exists for every configured scheme.
    """
    rng = random.Random(_RNG_SEED)
    inserted = 0

    for slug, config in SCHEME_OUTCOMES.items():
        version = db.execute(
            select(SchemeVersion)
            .join(Scheme, Scheme.id == SchemeVersion.scheme_id)
            .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
        ).scalar_one_or_none()
        if version is None:
            continue

        already_seeded = db.execute(
            select(Outcome.id)
            .join(Outcome.application)
            .where(
                Application.scheme_version_id == version.id,
                Outcome.notes.like(f"{SYNTHETIC_MARKER}%"),
            )
            .limit(1)
        ).first()
        if already_seeded is not None:
            continue

        outcomes = [OutcomeType.APPROVED] * config["approved"] + [
            OutcomeType.REJECTED
        ] * config["rejected"]
        rng.shuffle(outcomes)

        base_date = datetime.now(UTC) - timedelta(days=200)
        for index, outcome_type in enumerate(outcomes):
            submitted_at = base_date + timedelta(days=index * 3)
            days_to_decision = max(10, int(rng.gauss(config["avg_days"], 15)))
            decided_at = submitted_at + timedelta(days=days_to_decision)
            turnover = rng.choice(TURNOVER_SAMPLES)

            application = Application(
                user_id=None,
                scheme_version_id=version.id,
                status=outcome_type.value,
                submitted_at=submitted_at,
                last_status_update=decided_at,
            )
            db.add(application)
            db.flush()  # populate application.id for the Outcome FK below

            rejection_reason = (
                rng.choice(config["rejection_reasons"])
                if outcome_type is OutcomeType.REJECTED
                else None
            )

            db.add(
                Outcome(
                    application_id=application.id,
                    outcome_type=outcome_type,
                    decided_at=decided_at,
                    rejection_reason=rejection_reason,
                    days_to_decision=days_to_decision,
                    applicant_turnover_band=turnover_band(turnover),
                    notes=(
                        f"{SYNTHETIC_MARKER} inserted by seed_synthetic_outcomes "
                        "for demo/calibration purposes."
                    ),
                )
            )
            inserted += 1

    db.commit()
    return inserted


def main() -> int:
    from bharat_os.db import get_session_factory

    with get_session_factory()() as session:
        count = seed_synthetic_outcomes(session)

    print(f"{count} synthetic outcome(s) inserted." if count else "Already seeded; nothing to do.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
