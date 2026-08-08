"""Tests for the scheme data freshness endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bharat_os.config import get_settings
from bharat_os.models.enums import CriterionType
from bharat_os.models.scheme import Authority, EligibilityCriterion, Scheme, SchemeVersion


def _seed_scheme_with_verification(
    session: Session,
    slug: str,
    *,
    verified_ats: list[datetime],
) -> None:
    """Seed a scheme whose criteria carry the given ``last_verified_at`` values.

    One criterion per timestamp given, so a test can control exactly which
    dates the freshness computation has to work with.
    """
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
        summary="Summary for tests.",
        scheme_type="grant",
        status="active",
        administering_ministry="Ministry of Testing",
        authority=authority,
        target_segments=["msme"],
        sectors=[],
        states=[],
        benefit_value_min=100000,
        benefit_value_max=2000000,
        benefit_description="Up to Rs 20 lakh.",
        application_difficulty="medium",
        effective_from=datetime.now(UTC),
        criteria=[
            EligibilityCriterion(
                criterion_type=CriterionType.HARD,
                description=f"Criterion verified at {verified_at.isoformat()}.",
                machine_readable_rule={
                    "op": "contains",
                    "field": "registrations",
                    "value": "dpiit",
                },
                source_url="https://example.gov.in/criteria",
                last_verified_at=verified_at,
                verified_by_human=True,
                display_order=index,
            )
            for index, verified_at in enumerate(verified_ats, start=1)
        ],
    )
    session.add(version)
    session.commit()


class TestListFreshness:
    def test_empty_catalogue_returns_empty_list(self, client: TestClient) -> None:
        assert client.get("/freshness/").json() == []

    def test_recently_verified_scheme_is_not_stale(
        self, client: TestClient, session: Session
    ) -> None:
        recent = datetime.now(UTC) - timedelta(days=5)
        _seed_scheme_with_verification(session, "fresh-scheme", verified_ats=[recent])

        body = client.get("/freshness/").json()
        assert len(body) == 1
        assert body[0]["scheme_slug"] == "fresh-scheme"
        assert body[0]["is_stale"] is False
        assert body[0]["stale_criterion_count"] == 0
        assert body[0]["days_since_last_verification"] >= 4

    def test_scheme_unverified_beyond_threshold_is_stale(
        self, client: TestClient, session: Session
    ) -> None:
        threshold = get_settings().staleness_threshold_days
        old = datetime.now(UTC) - timedelta(days=threshold + 10)
        _seed_scheme_with_verification(session, "stale-scheme", verified_ats=[old])

        body = client.get("/freshness/").json()
        assert len(body) == 1
        assert body[0]["scheme_slug"] == "stale-scheme"
        assert body[0]["is_stale"] is True
        assert body[0]["stale_criterion_count"] == 1

    def test_staleness_is_driven_by_the_oldest_criterion_not_the_newest(
        self, client: TestClient, session: Session
    ) -> None:
        """A scheme with one fresh and one stale criterion must be reported
        stale overall - the newest check must not paper over the oldest."""
        threshold = get_settings().staleness_threshold_days
        recent = datetime.now(UTC) - timedelta(days=1)
        old = datetime.now(UTC) - timedelta(days=threshold + 10)
        _seed_scheme_with_verification(session, "mixed-scheme", verified_ats=[recent, old])

        body = client.get("/freshness/").json()
        assert body[0]["is_stale"] is True
        assert body[0]["stale_criterion_count"] == 1
        assert body[0]["total_criterion_count"] == 2

    def test_oldest_scheme_sorts_first(self, client: TestClient, session: Session) -> None:
        newer = datetime.now(UTC) - timedelta(days=1)
        older = datetime.now(UTC) - timedelta(days=200)
        _seed_scheme_with_verification(session, "newer-scheme", verified_ats=[newer])
        _seed_scheme_with_verification(session, "older-scheme", verified_ats=[older])

        slugs = [row["scheme_slug"] for row in client.get("/freshness/").json()]
        assert slugs == ["older-scheme", "newer-scheme"]

    def test_only_current_version_is_reported(self, client: TestClient, session: Session) -> None:
        """A superseded version must not appear alongside the current one."""
        recent = datetime.now(UTC) - timedelta(days=1)
        _seed_scheme_with_verification(session, "versioned-scheme", verified_ats=[recent])

        body = client.get("/freshness/").json()
        assert len(body) == 1


class TestGetSchemeFreshness:
    def test_returns_report_for_one_scheme(self, client: TestClient, session: Session) -> None:
        recent = datetime.now(UTC) - timedelta(days=2)
        _seed_scheme_with_verification(session, "sisfs", verified_ats=[recent])

        body = client.get("/freshness/sisfs").json()
        assert body["scheme_slug"] == "sisfs"
        assert body["is_stale"] is False
        assert body["staleness_threshold_days"] == get_settings().staleness_threshold_days

    def test_unknown_slug_returns_404(self, client: TestClient) -> None:
        response = client.get("/freshness/does-not-exist")
        assert response.status_code == 404
        assert "does-not-exist" in response.json()["detail"]
