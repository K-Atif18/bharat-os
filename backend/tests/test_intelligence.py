"""Tests for the outcome intelligence API and the synthetic outcome seed."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bharat_os.api.intelligence import SYNTHETIC_MARKER
from bharat_os.models.application import Application, Outcome
from bharat_os.models.enums import OutcomeType
from bharat_os.models.scheme import Authority, Scheme, SchemeVersion
from bharat_os.seed.seed_synthetic_outcomes import SCHEME_OUTCOMES, seed_synthetic_outcomes


def _seed_scheme(session: Session, slug: str) -> SchemeVersion:
    authority = Authority(
        slug=f"authority-{slug}",
        name="Ministry of Testing",
        authority_type="ministry",
        portal_url="https://example.gov.in",
    )
    version = SchemeVersion(
        scheme=Scheme(slug=slug),
        version=1,
        is_current=True,
        name=f"Scheme {slug}",
        summary="For intelligence tests.",
        scheme_type="grant",
        status="active",
        administering_ministry="Ministry of Testing",
        authority=authority,
        target_segments=["msme"],
        sectors=[],
        states=[],
        benefit_description="Up to Rs 10 lakh.",
        application_difficulty="medium",
        effective_from=datetime.now(UTC),
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


def _add_outcome(
    session: Session,
    version: SchemeVersion,
    *,
    outcome_type: OutcomeType,
    turnover_band: str | None = None,
    rejection_reason: str | None = None,
    days_to_decision: int | None = None,
    synthetic: bool = False,
) -> None:
    application = Application(user_id=None, scheme_version_id=version.id, status="approved")
    session.add(application)
    session.flush()
    session.add(
        Outcome(
            application_id=application.id,
            outcome_type=outcome_type,
            rejection_reason=rejection_reason,
            days_to_decision=days_to_decision,
            applicant_turnover_band=turnover_band,
            notes=f"{SYNTHETIC_MARKER} test row" if synthetic else "reported by a real applicant",
        )
    )
    session.commit()


class TestGetSchemeIntelligence:
    def test_unknown_slug_returns_404(self, client: TestClient) -> None:
        response = client.get("/intelligence/does-not-exist")
        assert response.status_code == 404

    def test_scheme_with_no_outcomes_reports_zero_not_an_error(
        self, client: TestClient, session: Session
    ) -> None:
        _seed_scheme(session, "no-outcomes-yet")
        body = client.get("/intelligence/no-outcomes-yet").json()
        assert body["total_outcomes_recorded"] == 0
        assert body["approval_rate"] is None
        assert "no outcomes" in body["data_note"].lower()

    def test_real_outcomes_are_labelled_as_real(
        self, client: TestClient, session: Session
    ) -> None:
        version = _seed_scheme(session, "real-outcomes-scheme")
        _add_outcome(session, version, outcome_type=OutcomeType.APPROVED, synthetic=False)
        _add_outcome(session, version, outcome_type=OutcomeType.REJECTED, synthetic=False)

        body = client.get("/intelligence/real-outcomes-scheme").json()
        assert body["has_real_outcomes"] is True
        assert body["total_outcomes_recorded"] == 2
        assert body["approval_rate"] == 0.5
        assert "synthetic" not in body["data_note"].lower()

    def test_synthetic_only_outcomes_are_labelled_as_synthetic(
        self, client: TestClient, session: Session
    ) -> None:
        version = _seed_scheme(session, "synthetic-only-scheme")
        _add_outcome(session, version, outcome_type=OutcomeType.APPROVED, synthetic=True)

        body = client.get("/intelligence/synthetic-only-scheme").json()
        assert body["has_real_outcomes"] is False
        assert "synthetic" in body["data_note"].lower()

    def test_one_real_outcome_among_synthetic_ones_still_counts_as_real(
        self, client: TestClient, session: Session
    ) -> None:
        """A single real report must not be diluted into 'mostly synthetic' -
        the presence of any real outcome makes the whole picture real,
        because hiding that behind a synthetic-data warning would
        understate confidence in data that is, in fact, real."""
        version = _seed_scheme(session, "mixed-scheme")
        _add_outcome(session, version, outcome_type=OutcomeType.APPROVED, synthetic=True)
        _add_outcome(session, version, outcome_type=OutcomeType.APPROVED, synthetic=False)

        body = client.get("/intelligence/mixed-scheme").json()
        assert body["has_real_outcomes"] is True

    def test_rejection_reasons_are_counted_and_ranked(
        self, client: TestClient, session: Session
    ) -> None:
        version = _seed_scheme(session, "rejection-reasons-scheme")
        _add_outcome(
            session,
            version,
            outcome_type=OutcomeType.REJECTED,
            rejection_reason="Missing audited financials",
            synthetic=True,
        )
        _add_outcome(
            session,
            version,
            outcome_type=OutcomeType.REJECTED,
            rejection_reason="Missing audited financials",
            synthetic=True,
        )
        _add_outcome(
            session,
            version,
            outcome_type=OutcomeType.REJECTED,
            rejection_reason="Turnover exceeded the cap",
            synthetic=True,
        )

        body = client.get("/intelligence/rejection-reasons-scheme").json()
        top = body["common_rejection_reasons"][0]
        assert top["reason"] == "Missing audited financials"
        assert top["count"] == 2

    def test_approval_rate_is_segmented_by_turnover_band(
        self, client: TestClient, session: Session
    ) -> None:
        version = _seed_scheme(session, "turnover-band-scheme")
        _add_outcome(
            session,
            version,
            outcome_type=OutcomeType.APPROVED,
            turnover_band="under-10l",
            synthetic=True,
        )
        _add_outcome(
            session,
            version,
            outcome_type=OutcomeType.REJECTED,
            turnover_band="1cr-5cr",
            synthetic=True,
        )

        body = client.get("/intelligence/turnover-band-scheme").json()
        assert body["approval_rate_by_turnover_band"]["under-10l"] == 1.0
        assert body["approval_rate_by_turnover_band"]["1cr-5cr"] == 0.0

    def test_average_days_to_decision_is_computed(
        self, client: TestClient, session: Session
    ) -> None:
        version = _seed_scheme(session, "timeline-scheme")
        _add_outcome(
            session,
            version,
            outcome_type=OutcomeType.APPROVED,
            days_to_decision=80,
            synthetic=True,
        )
        _add_outcome(
            session,
            version,
            outcome_type=OutcomeType.APPROVED,
            days_to_decision=100,
            synthetic=True,
        )

        body = client.get("/intelligence/timeline-scheme").json()
        assert body["average_days_to_decision"] == 90.0

    def test_unauthenticated_access_is_allowed(self, client: TestClient) -> None:
        """Aggregate, de-identified scheme statistics are not user data -
        same reasoning as /schemes, /freshness, /calibration."""
        client.cookies.clear()
        response = client.get("/intelligence/does-not-exist")
        # 404, not 401 - the route itself does not require a session.
        assert response.status_code == 404


class TestSeedSyntheticOutcomes:
    def test_seeding_against_a_missing_scheme_is_skipped_not_an_error(
        self, session: Session
    ) -> None:
        """None of SCHEME_OUTCOMES' slugs exist in this test's empty corpus -
        the seed must return 0, not raise, since the curated corpus can
        change independently of this file."""
        count = seed_synthetic_outcomes(session)
        assert count == 0

    def test_seeding_inserts_the_configured_split_for_an_existing_scheme(
        self, session: Session
    ) -> None:
        slug = next(iter(SCHEME_OUTCOMES))
        config = SCHEME_OUTCOMES[slug]
        _seed_scheme(session, slug)

        count = seed_synthetic_outcomes(session)

        assert count == config["approved"] + config["rejected"]

    def test_seeding_twice_does_not_duplicate(self, session: Session) -> None:
        slug = next(iter(SCHEME_OUTCOMES))
        _seed_scheme(session, slug)

        first = seed_synthetic_outcomes(session)
        second = seed_synthetic_outcomes(session)

        assert first > 0
        assert second == 0

    def test_every_inserted_outcome_is_marked_synthetic(self, session: Session) -> None:
        from sqlalchemy import select

        slug = next(iter(SCHEME_OUTCOMES))
        _seed_scheme(session, slug)
        seed_synthetic_outcomes(session)

        notes = session.scalars(select(Outcome.notes)).all()
        assert notes
        assert all(note.startswith(SYNTHETIC_MARKER) for note in notes)

    def test_every_inserted_application_has_no_user(self, session: Session) -> None:
        from sqlalchemy import select

        slug = next(iter(SCHEME_OUTCOMES))
        _seed_scheme(session, slug)
        seed_synthetic_outcomes(session)

        user_ids = session.scalars(select(Application.user_id)).all()
        assert user_ids
        assert all(uid is None for uid in user_ids)
