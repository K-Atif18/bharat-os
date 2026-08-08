"""Evaluate representative personas against the whole corpus, with no AI involved.

Run with::

    python -m bharat_os.scripts.demo_eligibility

Every line of output is reproducible from the profile and the curated rules. That
is the point of the exercise: before any language model is introduced, the system
already produces explainable, auditable verdicts.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bharat_os.db import get_session_factory
from bharat_os.engine import ApplicantProfile, assess_hard_criteria
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.services.eligibility import hard_criteria, soft_criteria

TODAY = date(2026, 7, 29)

PERSONAS: dict[str, ApplicantProfile] = {
    "Priya — DPIIT-recognised edtech startup, Pune, 8 staff, Rs 12L turnover": ApplicantProfile(
        state="Maharashtra",
        district="Pune",
        sector="edtech",
        stage="early",
        employee_count=8,
        annual_turnover_inr=1_200_000,
        social_category="general",
        is_woman_led=True,
        incorporation_date=date(2025, 3, 1),
        registrations=frozenset({"dpiit", "gst", "company_incorporation"}),
        as_of=TODAY,
    ),
    "Ramesh — Udyam-registered auto parts manufacturer, Ludhiana, Rs 4Cr": ApplicantProfile(
        state="Punjab",
        district="Ludhiana",
        sector="manufacturing",
        stage="growth",
        employee_count=42,
        annual_turnover_inr=40_000_000,
        social_category="obc",
        is_woman_led=False,
        incorporation_date=date(2016, 6, 15),
        registrations=frozenset({"udyam", "gst"}),
        as_of=TODAY,
    ),
    "Lakshmi — unregistered handloom unit, rural Tamil Nadu, turnover not shared": (
        ApplicantProfile(
            state="Tamil Nadu",
            sector="handicrafts",
            stage="idea",
            employee_count=3,
            annual_turnover_inr=None,  # deliberately withheld
            social_category="sc",
            is_woman_led=True,
            incorporation_date=None,  # not incorporated
            registrations=frozenset(),
            registrations_declared=True,
            as_of=TODAY,
        )
    ),
}

SYMBOL = {"met": "OK ", "unmet": "NO ", "cannot_verify": "?? "}


def main() -> int:
    with get_session_factory()() as session:
        rows = session.execute(
            select(Scheme, SchemeVersion)
            .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
            .where(SchemeVersion.is_current.is_(True))
            .options(selectinload(SchemeVersion.criteria))
            .order_by(Scheme.slug)
        ).all()

        if not rows:
            print("No schemes loaded. Run `make seed` first.")
            return 1

        for label, profile in PERSONAS.items():
            print("=" * 78)
            print(label)
            print("=" * 78)

            for scheme, version in rows:
                criteria = hard_criteria(version)
                assessment = assess_hard_criteria(criteria, profile)
                soft_count = len(soft_criteria(version))

                if assessment.total == 0:
                    verdict = "no machine-decidable criteria"
                elif assessment.has_disqualifier:
                    verdict = "ruled out on a hard requirement"
                elif assessment.unverifiable:
                    verdict = f"{len(assessment.met)}/{assessment.total} met, needs more data"
                else:
                    verdict = f"all {assessment.total} hard criteria met"

                print(f"\n  {scheme.slug:34} {verdict}")
                if soft_count:
                    print(f"  {'':34} plus {soft_count} criteria needing judgement")

                for criterion in criteria:
                    result = assessment.results[criterion.key]
                    print(f"    {SYMBOL[result.state.value]}{criterion.description[:62]}")
                    print(f"        {result.reason[:100]}")

            print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
