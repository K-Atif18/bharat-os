"""Tests for the live confidence calibration endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bharat_os.models.application import Application, Outcome
from bharat_os.models.enums import CriterionType
from bharat_os.models.scheme import EligibilityCriterion, Scheme, SchemeVersion


def _seed_application_with_outcome(
    session: Session, *, slug: str, outcome_type: str = "rejected"
) -> None:
    """An application with a recorded outcome, but - honestly, as the real
    schema stands today - no ``confidence_at_submission`` to pair it with.
    Exists to prove the endpoint does not mistake "an outcome exists" for
    "a calibration case exists"; those are different claims.
    """
    version = SchemeVersion(
        scheme=Scheme(slug=slug),
        version=1,
        is_current=True,
        name=f"Scheme {slug}",
        summary="For calibration tests.",
        scheme_type="grant",
        status="active",
        administering_ministry="Ministry of Testing",
        target_segments=["msme"],
        sectors=[],
        states=[],
        benefit_description="Up to Rs 10 lakh.",
        application_difficulty="medium",
        effective_from=datetime.now(UTC),
        criteria=[
            EligibilityCriterion(
                criterion_type=CriterionType.SOFT,
                description="Must demonstrate innovation.",
                source_url="https://example.gov.in/criteria",
                last_verified_at=datetime.now(UTC),
                verified_by_human=True,
                display_order=1,
            )
        ],
    )
    application = Application(user_id=None, scheme_version=version, status="rejected")
    application.outcome = Outcome(outcome_type=outcome_type)
    session.add(application)
    session.commit()


class TestGetCalibration:
    def test_falls_back_to_synthetic_fixtures_when_no_real_cases_exist(
        self, client: TestClient
    ) -> None:
        """With an empty outcome table (today's honest default state), the
        endpoint must serve the synthetic fixtures and say so - not report
        zero data, and not silently pretend the fixtures are real."""
        body = client.get("/calibration/").json()
        assert body["has_real_outcomes"] is False
        assert body["warning"] is not None
        assert "synthetic" in body["warning"].lower()
        assert body["sample_size"] > 0
        assert len(body["buckets"]) > 0

    def test_recorded_outcomes_alone_do_not_count_as_real_calibration_cases(
        self, client: TestClient, session: Session
    ) -> None:
        """An Outcome row existing is not the same claim as a calibration case
        existing - a case needs a predicted confidence to pair it with, which
        the current Application model does not yet record. Seeding an
        outcome must not flip has_real_outcomes to True."""
        _seed_application_with_outcome(session, slug="calibration-test-scheme")

        body = client.get("/calibration/").json()
        assert body["has_real_outcomes"] is False
        assert body["warning"] is not None

    def test_response_reports_the_configured_tolerance_relevant_fields(
        self, client: TestClient
    ) -> None:
        body = client.get("/calibration/").json()
        assert body["expected_calibration_error"] is not None
        assert 0.0 <= body["expected_calibration_error"] <= 1.0
        assert body["overall_direction"] in {
            "overconfident",
            "underconfident",
            "well calibrated",
        }

    def test_buckets_are_shaped_for_a_reliability_diagram(self, client: TestClient) -> None:
        body = client.get("/calibration/").json()
        for bucket in body["buckets"]:
            assert bucket["lower"] < bucket["upper"]
            assert bucket["count"] >= 0
            assert 0.0 <= bucket["mean_predicted"] <= 1.0 or bucket["count"] == 0
            assert bucket["direction"] in {
                "overconfident",
                "underconfident",
                "well calibrated",
                "no data",
            }

    def test_unauthenticated_access_is_allowed(self, client: TestClient) -> None:
        """Calibration is a property of the model, not of any user - same
        reasoning as /schemes and /freshness."""
        client.cookies.clear()
        response = client.get("/calibration/")
        assert response.status_code == 200
