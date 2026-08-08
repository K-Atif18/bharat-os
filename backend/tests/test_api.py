"""API smoke tests against a real database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bharat_os.models.enums import CriterionType
from bharat_os.models.scheme import Authority, EligibilityCriterion, Scheme, SchemeVersion

VERIFIED_AT = datetime.now(UTC) - timedelta(days=5)


def _seed_scheme(session: Session, slug: str, *, segments: list[str], states: list[str]) -> None:
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
        target_segments=segments,
        sectors=[],
        states=states,
        benefit_value_min=100000,
        benefit_value_max=2000000,
        benefit_description="Up to Rs 20 lakh.",
        application_difficulty="medium",
        effective_from=datetime.now(UTC),
        criteria=[
            EligibilityCriterion(
                criterion_type=CriterionType.HARD,
                description="Must hold DPIIT recognition.",
                machine_readable_rule={
                    "op": "contains",
                    "field": "registrations",
                    "value": "dpiit",
                },
                source_url="https://example.gov.in/criteria",
                last_verified_at=VERIFIED_AT,
                verified_by_human=True,
                display_order=1,
            )
        ],
    )
    session.add(version)
    session.commit()


class TestHealth:
    def test_reports_ok_with_reachable_database(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "reachable"
        assert body["scheme_count"] == 0


class TestListSchemes:
    def test_empty_catalogue_returns_empty_list(self, client: TestClient) -> None:
        assert client.get("/schemes").json() == []

    def test_lists_current_schemes(self, client: TestClient, session: Session) -> None:
        _seed_scheme(session, "sisfs", segments=["startup"], states=[])
        body = client.get("/schemes").json()
        assert len(body) == 1
        assert body[0]["slug"] == "sisfs"
        assert body[0]["version"] == 1
        assert body[0]["benefit_value_max"] == 2000000

    def test_filters_by_segment(self, client: TestClient, session: Session) -> None:
        _seed_scheme(session, "startup-only", segments=["startup"], states=[])
        _seed_scheme(session, "msme-only", segments=["msme"], states=[])
        slugs = [s["slug"] for s in client.get("/schemes?segment=msme").json()]
        assert slugs == ["msme-only"]

    def test_all_india_schemes_survive_a_state_filter(
        self, client: TestClient, session: Session
    ) -> None:
        """An empty ``states`` list means all-India, so it must not be filtered out."""
        _seed_scheme(session, "all-india", segments=["msme"], states=[])
        _seed_scheme(session, "kerala-only", segments=["msme"], states=["Kerala"])
        slugs = sorted(s["slug"] for s in client.get("/schemes?state=Maharashtra").json())
        assert slugs == ["all-india"]


class TestGetScheme:
    def test_returns_detail_with_provenance(self, client: TestClient, session: Session) -> None:
        _seed_scheme(session, "cgtmse", segments=["msme"], states=[])
        body = client.get("/schemes/cgtmse").json()
        assert body["slug"] == "cgtmse"
        assert body["authority"]["name"] == "Ministry of Testing"
        assert len(body["criteria"]) == 1
        criterion = body["criteria"][0]
        assert criterion["source_url"] == "https://example.gov.in/criteria"
        # Staleness is computed for the client rather than left implicit.
        assert criterion["days_since_verified"] >= 4

    def test_unknown_slug_returns_404(self, client: TestClient) -> None:
        response = client.get("/schemes/does-not-exist")
        assert response.status_code == 404
        assert "does-not-exist" in response.json()["detail"]

    def test_unknown_version_returns_404(self, client: TestClient, session: Session) -> None:
        _seed_scheme(session, "pmegp", segments=["msme"], states=[])
        response = client.get("/schemes/pmegp?version=7")
        assert response.status_code == 404
        assert "version 7" in response.json()["detail"]
